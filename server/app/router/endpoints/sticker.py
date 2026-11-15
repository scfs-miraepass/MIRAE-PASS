from datetime import datetime
from math import ceil
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query, Response, status
from pydantic import BaseModel, Field, field_serializer
from sqlalchemy import and_
from sqlalchemy.orm import aliased
from sqlmodel import col, func, select

from app.core import LoginDep, ServiceClient
from app.core.cache_events import on_sticker_changed
from app.core.redis_keys import Keys
from app.schemas import StickerHistory, StickerReset, UserPermission, Users, UserSearch, UserType
from app.schemas.core import SchemaCore
from app.schemas.response import ErrorResponse, ResponseModel

router = APIRouter(prefix="/sticker", tags=["sticker"])
client = ServiceClient()

STICKER_MAX = 3
"""학생 한 명이 현재 집계 기간 동안 보유할 수 있는 최대 스티커 수"""
MAX_PAGE_LIMIT = 100
STICKER_TIMEZONE = ZoneInfo("Asia/Seoul")

PERMISSION_DENIED = HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied.")


# ---------- 요청 / 응답 모델 ----------


class StickerOperation(BaseModel):
    user_id: int = Field(description="대상 학생의 고유 ID (학번)")
    amount: int = Field(1, ge=1, le=STICKER_MAX, description=f"처리할 스티커 수 (1~{STICKER_MAX})")
    memo: str | None = Field(None, max_length=100, description="메모")


class StickerClassOperation(BaseModel):
    grade: int = Field(ge=1, le=3, description="대상 학년")
    number: int = Field(ge=1, description="대상 반")
    amount: int = Field(1, ge=1, le=STICKER_MAX, description=f"전달할 스티커 수 (1~{STICKER_MAX})")
    memo: str | None = Field(None, max_length=100, description="메모")


class StickerBalance(BaseModel):
    user_id: int = Field(description="학생의 고유 ID")
    count: int = Field(description="현재 집계 기간 내 보유 스티커 수")
    max: int = Field(description="보유 가능한 최대 스티커 수")
    period_start: datetime = Field(description="현재 집계 기간 시작 시각")

    @field_serializer("period_start")
    def serialize_period_start(self, dt: Any, _info):
        if isinstance(dt, datetime):
            return SchemaCore.sync_timezone(dt).isoformat()
        return dt


class StickerRankingResponse(BaseModel):
    id: int = Field(description="학생의 고유 ID (학번)")
    name: str = Field(description="이름")
    grade: int | None = Field(description="학년")
    number: int | None = Field(description="반")
    count: int = Field(description="현재 집계 기간 내 보유 스티커 수")
    rank: int = Field(description="전체 학생 기준 순위")


class StickerClassRankingResponse(BaseModel):
    grade: int = Field(description="학년")
    number: int = Field(description="반")
    count: int = Field(description="학급 스티커 합계 (학생 보유 + 교사 전달)")
    teacher_count: int = Field(description="교사가 이 학급에 전달한 스티커 수")
    rank: int = Field(description="합계 기준 순위")


class StickerHistoryItem(BaseModel):
    id: int
    user_id: int = Field(description="대상 유저(학생/교사)의 고유 ID")
    user_name: str | None = Field(description="대상 유저 이름")
    user_type: str | None = Field(description="대상 유저 타입 (student / teacher)")
    class_grade: int | None = Field(description="교사가 학급에 전달한 기록인 경우 대상 학년")
    class_number: int | None = Field(description="교사가 학급에 전달한 기록인 경우 대상 반")
    grade: int | None = Field(description="대상 학생 학년")
    number: int | None = Field(description="대상 학생 반")
    amount: int = Field(description="변동 수량 (지급 +, 회수 -)")
    actor_id: int | None = Field(description="처리한 유저의 고유 ID")
    actor_name: str | None = Field(description="처리한 유저 이름")
    memo: str | None
    created_at: datetime

    @field_serializer("created_at")
    def serialize_created_at(self, dt: Any, _info):
        if isinstance(dt, datetime):
            return SchemaCore.sync_timezone(dt).isoformat()
        return dt


class StickerHistoryPage(BaseModel):
    period_start: datetime = Field(description="현재 집계 기간 시작 시각")
    items: list[StickerHistoryItem]

    @field_serializer("period_start")
    def serialize_period_start(self, dt: Any, _info):
        if isinstance(dt, datetime):
            return SchemaCore.sync_timezone(dt).isoformat()
        return dt


# ---------- 헬퍼 ----------


async def _get_period_start(session) -> tuple[datetime, str]:
    """
    현재 집계 기간의 시작 시각을 반환합니다.

    `max(이번 달 1일 00:00 KST, 가장 최근 수동 초기화 시각)` 을 DB 서버 시간대로 변환해 반환하며,
    두 번째 값은 캐시 Key 용 문자열(YYYYMMDDHHMMSS) 입니다.
    """
    now_kst = SchemaCore.now().astimezone(STICKER_TIMEZONE)
    month_start = now_kst.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    start = month_start.astimezone(SchemaCore.timezone)

    latest_reset = (await session.execute(select(func.max(StickerReset.reset_at)))).scalar()
    if latest_reset is not None:
        latest_reset = SchemaCore.sync_timezone(latest_reset)
        if latest_reset > start:
            start = latest_reset

    return start, start.astimezone(STICKER_TIMEZONE).strftime("%Y%m%d%H%M%S")


async def _get_held(session, user_id: int, period_start: datetime) -> int:
    """학생이 현재 집계 기간 동안 보유한 스티커 수"""
    result = await session.execute(
        select(func.coalesce(func.sum(StickerHistory.amount), 0)).where(
            StickerHistory.user_id == user_id,
            StickerHistory.created_at >= period_start,
        )
    )
    return int(result.scalar() or 0)


async def _get_student_count(session) -> int:
    """전체 학생 수 (포인트 랭킹과 동일한 캐시 Key 사용)"""
    count_cache_key = Keys.Ranking.COUNT(type="student")
    cached = await client.redis.get(count_cache_key)
    if cached is not None:
        return int(cached)
    count = (
        await session.execute(select(func.count()).select_from(Users).where(Users.type == UserType.student))
    ).scalar() or 0
    await client.redis.set(count_cache_key, count)
    return count


def _ranking_search_condition(ranked, q: str):
    """`/search` 와 동일한 규칙으로 랭킹 서브쿼리에 적용할 검색 조건을 만듭니다. None이면 결과가 없는 검색입니다."""
    q = q.replace(" ", "")
    if q.isdigit():
        # 학번은 총 4자이므로 4자 미만일 경우 빈 결과
        if len(q) < 4:
            return None
        return ranked.c.id == int(q)

    decomposed = client.normalize_and_decompose(q)
    matched_ids = select(UserSearch.user_id).where(col(UserSearch.value).like(f"%{decomposed}%"))
    return ranked.c.id.in_(matched_ids)


async def _apply_sticker_change(
    actor_id: int,
    data: StickerOperation,
    *,
    revoke: bool,
) -> StickerBalance:
    """스티커 지급(revoke=False) 또는 회수(revoke=True)를 처리하고 변경 후 보유 수를 반환합니다."""
    async with client.session as session:
        target = await client.get_user(data.user_id, lock=True)
        if target is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if target.type not in (UserType.student, UserType.teacher):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Stickers can only be given to students or teachers."
            )

        period_start, _ = await _get_period_start(session)
        held = await _get_held(session, target.id, period_start)

        if revoke:
            if held - data.amount < 0:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Not enough stickers to revoke. (held: {held})",
                )
            changed = -data.amount
        else:
            if held + data.amount > STICKER_MAX:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Sticker limit exceeded. (held: {held}, max: {STICKER_MAX})",
                )
            changed = data.amount

        session.add(StickerHistory(user_id=target.id, amount=changed, actor_id=actor_id, memo=data.memo))
        new_count = held + changed

    await on_sticker_changed()
    action = "회수" if revoke else "지급"
    client.logs.service.info(
        f"{actor_id} -> {target.id}({target.name}) 스티커 {data.amount}개 {action} (보유: {held} -> {new_count})"
    )
    return StickerBalance(user_id=target.id, count=new_count, max=STICKER_MAX, period_start=period_start)


# ---------- 엔드포인트 ----------


@router.post(
    "",
    operation_id="grant_sticker",
    response_model=ResponseModel[StickerBalance],
    responses={
        200: {"description": "정상 처리"},
        400: {"model": ErrorResponse, "description": "학생이 아닌 유저에게 지급 시도"},
        403: {"model": ErrorResponse, "description": "권한이 없음"},
        404: {"model": ErrorResponse, "description": "유저를 찾을 수 없음"},
        409: {"model": ErrorResponse, "description": f"보유 한도({STICKER_MAX}개) 초과"},
    },
    summary="스티커 지급",
    description=f"학생에게 스티커를 1~{STICKER_MAX}개 지급합니다. 현재 집계 기간 내 보유 수는 {STICKER_MAX}개를 넘을 수 없습니다.",
)
async def grant_sticker(data: StickerOperation, auth: LoginDep):
    user, _ = auth
    if not (user.has_permission(UserPermission.GIVE_STICKER) or user.has_permission(UserPermission.MANAGE_STICKER)):
        raise PERMISSION_DENIED

    balance = await _apply_sticker_change(user.id, data, revoke=False)
    return ResponseModel[StickerBalance](success=True, data=balance)


@router.post(
    "/revoke",
    operation_id="revoke_sticker",
    response_model=ResponseModel[StickerBalance],
    responses={
        200: {"description": "정상 처리"},
        400: {"model": ErrorResponse, "description": "학생이 아닌 유저"},
        403: {"model": ErrorResponse, "description": "권한이 없음"},
        404: {"model": ErrorResponse, "description": "유저를 찾을 수 없음"},
        409: {"model": ErrorResponse, "description": "보유 수보다 많이 회수 시도"},
    },
    summary="스티커 회수",
    description="학생의 스티커를 회수합니다. 현재 집계 기간 내 보유 수 이하로만 회수할 수 있습니다.",
)
async def revoke_sticker(data: StickerOperation, auth: LoginDep):
    user, _ = auth
    if not user.has_permission(UserPermission.MANAGE_STICKER):
        raise PERMISSION_DENIED

    balance = await _apply_sticker_change(user.id, data, revoke=True)
    return ResponseModel[StickerBalance](success=True, data=balance)


@router.post(
    "/class",
    operation_id="give_sticker_to_class",
    response_model=ResponseModel[StickerBalance],
    responses={
        200: {"description": "정상 처리"},
        403: {"model": ErrorResponse, "description": "권한이 없음"},
        404: {"model": ErrorResponse, "description": "해당 학급(학생)이 없음"},
        409: {"model": ErrorResponse, "description": "보유한 스티커가 부족함"},
    },
    summary="학급에 스티커 전달 (교사)",
    description="교사가 보유한 스티커를 원하는 학급에 전달합니다. 전달한 만큼 교사 보유 수가 줄고 학급 합계에 더해집니다.",
)
async def give_sticker_to_class(data: StickerClassOperation, auth: LoginDep):
    user, _ = auth
    if not user.has_permission(UserPermission.GIVE_CLASS_STICKER):
        raise PERMISSION_DENIED

    async with client.session as session:
        # 보유 수 계산 중 동시 변경을 막기 위해 자신의 행 잠금
        await client.get_user(user.id, lock=True)

        period_start, _ = await _get_period_start(session)
        held = await _get_held(session, user.id, period_start)
        if held < data.amount:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Not enough stickers. (held: {held})",
            )

        class_size = (
            await session.execute(
                select(func.count())
                .select_from(Users)
                .where(Users.type == UserType.student, Users.grade == data.grade, Users.number == data.number)
            )
        ).scalar() or 0
        if class_size == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")

        session.add(
            StickerHistory(
                user_id=user.id,
                amount=-data.amount,
                actor_id=user.id,
                memo=data.memo,
                class_grade=data.grade,
                class_number=data.number,
            )
        )
        new_count = held - data.amount

    await on_sticker_changed()
    client.logs.service.info(
        f"{user.id}({user.name})가 {data.grade}학년 {data.number}반에 스티커 {data.amount}개 전달 (보유: {held} -> {new_count})"
    )
    return ResponseModel[StickerBalance](
        success=True,
        data=StickerBalance(user_id=user.id, count=new_count, max=STICKER_MAX, period_start=period_start),
    )


@router.post(
    "/reset",
    operation_id="reset_stickers",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "정상 처리"},
        403: {"model": ErrorResponse, "description": "권한이 없음"},
    },
    summary="스티커 수동 초기화",
    description="모든 학생의 현재 스티커 보유 수를 0으로 만듭니다. 기록은 삭제되지 않으며 새 집계 기간이 시작됩니다.",
)
async def reset_stickers(auth: LoginDep):
    user, _ = auth
    if not user.has_permission(UserPermission.MANAGE_STICKER):
        raise PERMISSION_DENIED

    async with client.session as session:
        session.add(StickerReset(reset_by_id=user.id))

    await on_sticker_changed()
    client.logs.service.info(f"{user.id}({user.name})가 스티커를 수동으로 초기화했습니다.")


@router.get(
    "/me",
    operation_id="get_my_sticker_balance",
    response_model=ResponseModel[StickerBalance],
    responses={
        200: {"description": "정상 처리"},
        403: {"model": ErrorResponse, "description": "권한이 없음"},
    },
    summary="내 스티커 보유 수 조회",
    description="현재 집계 기간 내 내 스티커 보유 수를 조회합니다. 학생/교사가 아닌 경우 0을 반환합니다.",
)
async def get_my_sticker_balance(auth: LoginDep):
    user, _ = auth
    if not user.has_permission(UserPermission.VIEW_STICKER):
        raise PERMISSION_DENIED

    async with client.session as session:
        period_start, _ = await _get_period_start(session)
        count = (
            await _get_held(session, user.id, period_start) if user.type in (UserType.student, UserType.teacher) else 0
        )

    return ResponseModel[StickerBalance](
        success=True, data=StickerBalance(user_id=user.id, count=count, max=STICKER_MAX, period_start=period_start)
    )


@router.get(
    "/users/{user_id}",
    operation_id="get_user_sticker_balance",
    response_model=ResponseModel[StickerBalance],
    responses={
        200: {"description": "정상 처리"},
        403: {"model": ErrorResponse, "description": "권한이 없음"},
        404: {"model": ErrorResponse, "description": "유저를 찾을 수 없음"},
    },
    summary="특정 학생 스티커 보유 수 조회",
    description="지급/관리 권한이 있는 유저가 특정 학생의 현재 스티커 보유 수를 조회합니다.",
)
async def get_user_sticker_balance(user_id: int, auth: LoginDep):
    user, _ = auth
    if not (user.has_permission(UserPermission.GIVE_STICKER) or user.has_permission(UserPermission.MANAGE_STICKER)):
        raise PERMISSION_DENIED

    async with client.session as session:
        target = await client.get_user(user_id, cache=True)
        if target is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        period_start, _ = await _get_period_start(session)
        count = await _get_held(session, target.id, period_start)

    return ResponseModel[StickerBalance](
        success=True, data=StickerBalance(user_id=target.id, count=count, max=STICKER_MAX, period_start=period_start)
    )


@router.get(
    "/ranking",
    operation_id="get_sticker_ranking",
    response_model=ResponseModel[list[StickerRankingResponse]],
    responses={
        200: {"description": "정상 처리"},
        403: {"model": ErrorResponse, "description": "권한이 없음"},
    },
    summary="스티커 개인 랭킹 조회",
    description="현재 집계 기간 내 스티커 보유 수 기준 학생 랭킹을 조회합니다. `q`로 이름(초성 포함) 또는 학번을 검색할 수 있으며, 검색 결과의 순위는 전체 기준 순위입니다.",
)
async def get_sticker_ranking(
    auth: LoginDep,
    response: Response,
    q: str | None = Query(None, description="검색어 (이름 또는 학번)"),
    limit: int = Query(20, ge=1, le=MAX_PAGE_LIMIT, description=f"페이지 당 데이터 갯수 (최대 {MAX_PAGE_LIMIT})"),
    offset: int = Query(0, ge=0),
):
    user, _ = auth
    if not user.has_permission(UserPermission.VIEW_STICKER):
        raise PERMISSION_DENIED

    q = (q or "").strip()

    async with client.session as session:
        period_start, period_key = await _get_period_start(session)

        cache_key = None
        if not q:
            count = await _get_student_count(session)
            ver = await client.redis.get_version(Keys.Sticker.VERSION())
            cache_key = Keys.Sticker.RANKING(ver=ver, period=period_key, limit=limit, offset=offset)
            cached = await client.redis.get(cache_key)
            if cached is not None:
                response.headers["X-MAX-PAGE"] = str(ceil(count / limit))
                return ResponseModel[list[StickerRankingResponse]](
                    success=True, data=[StickerRankingResponse(**item) for item in cached]
                )

        period_sum = (
            select(StickerHistory.user_id, func.sum(StickerHistory.amount).label("cnt"))
            .where(StickerHistory.created_at >= period_start)
            .group_by(col(StickerHistory.user_id))
            .subquery()
        )
        cnt = func.coalesce(period_sum.c.cnt, 0)
        # 검색 결과에서도 전체 기준 순위를 유지하기 위해 순위를 먼저 계산한 뒤 바깥에서 필터링
        ranked = (
            select(
                col(Users.id).label("id"),
                col(Users.name).label("name"),
                col(Users.grade).label("grade"),
                col(Users.number).label("number"),
                cnt.label("count"),
                func.dense_rank().over(order_by=cnt.desc()).label("rank"),
            )
            .outerjoin(period_sum, period_sum.c.user_id == Users.id)
            .where(Users.type == UserType.student)
            .subquery()
        )

        base = select(ranked)
        if q:
            condition = _ranking_search_condition(ranked, q)
            if condition is None:
                response.headers["X-MAX-PAGE"] = "0"
                return ResponseModel[list[StickerRankingResponse]](success=True, data=[])
            base = base.where(condition)
            count = (await session.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0

        query = base.order_by(ranked.c.count.desc(), ranked.c.id.asc()).limit(limit).offset(offset)
        rows = (await session.execute(query)).all()

    rankings = [
        StickerRankingResponse(
            id=r.id, name=r.name, grade=r.grade, number=r.number, count=int(r.count), rank=int(r.rank)
        )
        for r in rows
    ]
    if cache_key is not None:
        await client.redis.set(cache_key, [item.model_dump() for item in rankings])

    response.headers["X-MAX-PAGE"] = str(ceil(count / limit))
    return ResponseModel[list[StickerRankingResponse]](success=True, data=rankings)


@router.get(
    "/ranking/class",
    operation_id="get_sticker_class_ranking",
    response_model=ResponseModel[list[StickerClassRankingResponse]],
    responses={
        200: {"description": "정상 처리"},
        403: {"model": ErrorResponse, "description": "권한이 없음"},
    },
    summary="스티커 학급 랭킹 조회",
    description="학급별(학년, 반) 스티커 합계를 조회합니다. 결과는 1학년 1반부터 학년, 반 순으로 정렬되며 `rank`는 합계 기준 순위입니다.",
)
async def get_sticker_class_ranking(auth: LoginDep):
    user, _ = auth
    if not user.has_permission(UserPermission.VIEW_STICKER):
        raise PERMISSION_DENIED

    async with client.session as session:
        period_start, period_key = await _get_period_start(session)
        ver = await client.redis.get_version(Keys.Sticker.VERSION())
        cache_key = Keys.Sticker.CLASS_RANKING(ver=ver, period=period_key)

        cached = await client.redis.get(cache_key)
        if cached is not None:
            return ResponseModel[list[StickerClassRankingResponse]](
                success=True, data=[StickerClassRankingResponse(**item) for item in cached]
            )

        # 1. 학급 학생들의 보유 합계
        total = func.coalesce(func.sum(StickerHistory.amount), 0)
        query = (
            select(col(Users.grade), col(Users.number), total.label("count"))
            .select_from(Users)
            .outerjoin(
                StickerHistory,
                and_(StickerHistory.user_id == Users.id, StickerHistory.created_at >= period_start),
            )
            .where(
                Users.type == UserType.student,
                col(Users.grade).isnot(None),
                col(Users.number).isnot(None),
            )
            .group_by(col(Users.grade), col(Users.number))
            .order_by(col(Users.grade).asc(), col(Users.number).asc())
        )
        rows = (await session.execute(query)).all()

        # 2. 교사가 학급에 전달한 합계 (전달 행은 amount가 음수이므로 부호를 뒤집어 합산)
        teacher_query = (
            select(
                col(StickerHistory.class_grade),
                col(StickerHistory.class_number),
                func.coalesce(func.sum(-StickerHistory.amount), 0).label("count"),
            )
            .where(
                col(StickerHistory.class_grade).isnot(None),
                col(StickerHistory.class_number).isnot(None),
                StickerHistory.created_at >= period_start,
            )
            .group_by(col(StickerHistory.class_grade), col(StickerHistory.class_number))
        )
        teacher_rows = (await session.execute(teacher_query)).all()

    teacher_of = {(r.class_grade, r.class_number): int(r.count) for r in teacher_rows}
    merged = [
        (
            r.grade,
            r.number,
            int(r.count) + teacher_of.get((r.grade, r.number), 0),
            teacher_of.get((r.grade, r.number), 0),
        )
        for r in rows
    ]

    # 합계 기준 dense rank 계산 (정렬 자체는 학년, 반 순 유지)
    counts = sorted({total for _, _, total, _ in merged}, reverse=True)
    rank_of = {c: i + 1 for i, c in enumerate(counts)}
    result = [
        StickerClassRankingResponse(grade=grade, number=number, count=total, teacher_count=teacher, rank=rank_of[total])
        for grade, number, total, teacher in merged
    ]
    await client.redis.set(cache_key, [item.model_dump() for item in result])

    return ResponseModel[list[StickerClassRankingResponse]](success=True, data=result)


@router.get(
    "/history",
    operation_id="get_sticker_history",
    response_model=ResponseModel[StickerHistoryPage],
    responses={
        200: {"description": "정상 처리"},
        403: {"model": ErrorResponse, "description": "권한이 없음"},
    },
    summary="스티커 기록 조회 (관리자)",
    description="현재 집계 기간 내 스티커 지급/회수/학급 전달 기록을 최신순으로 조회합니다. `user_id`로 특정 유저만 필터링할 수 있습니다.",
)
async def get_sticker_history(
    auth: LoginDep,
    response: Response,
    user_id: int | None = Query(None, description="특정 학생의 기록만 조회"),
    limit: int = Query(20, ge=1, le=MAX_PAGE_LIMIT, description=f"페이지 당 데이터 갯수 (최대 {MAX_PAGE_LIMIT})"),
    offset: int = Query(0, ge=0),
):
    user, _ = auth
    if not user.has_permission(UserPermission.MANAGE_STICKER):
        raise PERMISSION_DENIED

    target = aliased(Users)
    actor = aliased(Users)

    async with client.session as session:
        period_start, _ = await _get_period_start(session)

        conditions: Any = [StickerHistory.created_at >= period_start]
        if user_id is not None:
            conditions.append(StickerHistory.user_id == user_id)

        count = (
            await session.execute(select(func.count()).select_from(StickerHistory).where(*conditions))
        ).scalar() or 0

        query = (
            select(
                StickerHistory,
                target.name.label("user_name"),
                target.type.label("user_type"),
                target.grade.label("grade"),
                target.number.label("number"),
                actor.name.label("actor_name"),
            )
            .outerjoin(target, target.id == StickerHistory.user_id)
            .outerjoin(actor, actor.id == StickerHistory.actor_id)
            .where(*conditions)
            .order_by(col(StickerHistory.created_at).desc(), col(StickerHistory.id).desc())
            .limit(limit)
            .offset(offset)
        )
        rows = (await session.execute(query)).all()

    items = [
        StickerHistoryItem(
            id=h.id,
            user_id=h.user_id,
            user_name=user_name,
            user_type=str(user_type) if user_type is not None else None,
            class_grade=h.class_grade,
            class_number=h.class_number,
            grade=grade,
            number=number,
            amount=h.amount,
            actor_id=h.actor_id,
            actor_name=actor_name,
            memo=h.memo,
            created_at=h.created_at,
        )
        for h, user_name, user_type, grade, number, actor_name in rows
    ]

    response.headers["X-MAX-PAGE"] = str(ceil(count / limit))
    return ResponseModel[StickerHistoryPage](
        success=True, data=StickerHistoryPage(period_start=period_start, items=items)
    )


@router.delete(
    "/history/{history_id}",
    operation_id="delete_sticker_history",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "정상 처리"},
        403: {"model": ErrorResponse, "description": "권한이 없음"},
        404: {"model": ErrorResponse, "description": "기록을 찾을 수 없음"},
        409: {"model": ErrorResponse, "description": "취소 시 학생의 보유 수가 0 미만이 됨"},
    },
    summary="스티커 기록 취소 (관리자)",
    description="스티커 지급/회수 기록 하나를 삭제해 해당 변동을 없던 것으로 만듭니다. 삭제 후 학생의 현재 기간 보유 수가 0 미만이 되는 경우 거부됩니다.",
)
async def delete_sticker_history(history_id: int, auth: LoginDep):
    user, _ = auth
    if not user.has_permission(UserPermission.MANAGE_STICKER):
        raise PERMISSION_DENIED

    async with client.session as session:
        history = (
            await session.execute(select(StickerHistory).where(StickerHistory.id == history_id))
        ).scalar_one_or_none()
        if history is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="History not found")

        # 보유 수 계산 중 동시 변경을 막기 위해 학생 행 잠금
        await client.get_user(history.user_id, lock=True)

        period_start, _ = await _get_period_start(session)
        created_at = SchemaCore.sync_timezone(history.created_at)
        if created_at >= period_start:
            held = await _get_held(session, history.user_id, period_start)
            if held - history.amount < 0:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cancelling this record would make the balance negative. (held: {held})",
                )

        await session.delete(history)

    await on_sticker_changed()
    client.logs.service.info(
        f"{user.id}({user.name})가 스티커 기록 #{history_id} (학생 {history.user_id}, {history.amount:+d})를 취소했습니다."
    )
