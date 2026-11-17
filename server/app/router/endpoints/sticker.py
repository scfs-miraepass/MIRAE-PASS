from datetime import datetime
from math import ceil
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Response, status
from pydantic import BaseModel, Field, field_serializer
from sqlalchemy import ColumnElement, Subquery, and_
from sqlalchemy.orm import aliased
from sqlmodel import col, func, select

from app.core import LoginDep, ServiceClient
from app.core.error import Conflict, LimitExceeded, NotFound
from app.core.redis_keys import Keys
from app.core.service.sticker import STICKER_MAX, STICKER_TARGET_TYPES, Sticker, StickerCount
from app.schemas import StickerHistory, UserPermission, Users, UserSearch, UserType
from app.schemas.core import SchemaCore
from app.schemas.response import ErrorResponse, ResponseModel

router = APIRouter(prefix="/sticker", tags=["sticker"])
client = ServiceClient()
MAX_PAGE_LIMIT = 100
MAX_BULK_TARGETS = 100


class StickerOperation(BaseModel):
    user_id: int = Field(..., description="대상 유저(학생 / 교사)의 고유 ID")
    amount: int = Field(1, ge=1, le=STICKER_MAX, description=f"처리할 스티커 수 (1~{STICKER_MAX})")
    memo: str | None = Field(None, max_length=100, description="메모")


class StickerClassOperation(BaseModel):
    grade: int = Field(..., ge=1, le=3, description="대상 학년")
    number: int = Field(..., ge=1, description="대상 반")
    amount: int = Field(1, ge=1, le=STICKER_MAX, description=f"전달할 스티커 수 (1~{STICKER_MAX})")
    memo: str | None = Field(None, max_length=100, description="메모")


class StickerBulkOperation(BaseModel):
    user_ids: list[int] = Field(
        ..., min_length=1, max_length=MAX_BULK_TARGETS, description=f"대상 유저 ID 목록 (1~{MAX_BULK_TARGETS}명)"
    )
    amount: int = Field(1, ge=1, le=STICKER_MAX, description=f"유저마다 지급할 스티커 수 (1~{STICKER_MAX})")
    memo: str | None = Field(None, max_length=100, description="메모")


class StickerBalance(BaseModel):
    user_id: int = Field(..., description="유저의 고유 ID")
    count: int = Field(..., description="현재 집계 기간 내 보유 스티커 수")
    max: int = Field(..., description="한 주 동안 받을 수 있는 최대 스티커 수")
    period_start: datetime = Field(..., description="현재 집계 기간 시작 시각")
    week_count: int = Field(..., description="이번 주에 지급받은 스티커 수 (학급 전달 제외)")
    week_start: datetime = Field(
        ..., description="이번 주 한도 계산 시작 시각 (월요일 00:00 KST, 수동 초기화가 있었다면 그 시각)"
    )

    @field_serializer("period_start", "week_start")
    def serialize_dt(self, dt: Any, _info):
        if isinstance(dt, datetime):
            return SchemaCore.sync_timezone(dt).isoformat()
        return dt


class StickerBulkFailure(BaseModel):
    user_id: int = Field(..., description="지급하지 못한 유저의 고유 ID")
    reason: str = Field(..., description="지급하지 못한 이유")


class StickerBulkGranted(StickerBalance):
    granted: int = Field(..., description="실제 지급된 수 (이번 주 남은 한도가 요청 수보다 적으면 요청 수보다 작음)")


class StickerBulkResult(BaseModel):
    succeeded: list[StickerBulkGranted] = Field(..., description="지급에 성공한 유저의 지급 후 보유 수와 실제 지급 수")
    failed: list[StickerBulkFailure] = Field(..., description="지급하지 못한 유저와 이유")


def _balance(user_id: int, result: StickerCount) -> StickerBalance:
    """
    서비스 계산 결과를 응답 모델로 바꿉니다.

    Args:
        user_id: 유저 ID
        result: 서비스가 계산한 보유 수

    Returns:
        StickerBalance
    """
    return StickerBalance(
        user_id=user_id,
        count=result.count,
        max=STICKER_MAX,
        period_start=result.period_start,
        week_count=result.week_count,
        week_start=result.week_start,
    )


class StickerRankingResponse(BaseModel):
    id: int = Field(..., description="학생의 고유 ID (학번)")
    name: str = Field(..., description="이름")
    grade: int | None = Field(..., description="학년")
    number: int | None = Field(..., description="반")
    count: int = Field(..., description="현재 집계 기간 내 보유 스티커 수")
    week_count: int = Field(..., description="이번 주에 지급받은 스티커 수 (하트 표시용, 0~최대 한도)")
    rank: int = Field(..., description="전체 학생 기준 순위")


class StickerClassRankingResponse(BaseModel):
    grade: int = Field(..., description="학년")
    number: int = Field(..., description="반")
    count: int = Field(..., description="학급 스티커 합계 (학생 보유 + 교사 전달)")
    teacher_count: int = Field(..., description="교사가 이 학급에 전달한 스티커 수")
    rank: int = Field(..., description="합계 기준 순위")


class StickerHistoryItem(BaseModel):
    id: int = Field(..., description="스티커 기록 ID")
    user_id: int = Field(..., description="대상 유저(학생 / 교사)의 고유 ID")
    user_name: str | None = Field(..., description="대상 유저 이름")
    user_type: UserType | None = Field(..., description="대상 유저 타입")
    class_grade: int | None = Field(..., description="교사가 학급에 전달한 기록인 경우 대상 학년")
    class_number: int | None = Field(..., description="교사가 학급에 전달한 기록인 경우 대상 반")
    grade: int | None = Field(..., description="대상 학생 학년")
    number: int | None = Field(..., description="대상 학생 반")
    amount: int = Field(..., description="변동 수량 (지급 +, 회수 · 학급 전달 -)")
    actor_id: int | None = Field(..., description="처리한 유저의 고유 ID")
    actor_name: str | None = Field(..., description="처리한 유저 이름")
    memo: str | None = Field(..., description="메모")
    created_at: datetime = Field(..., description="처리 일시")

    @field_serializer("created_at")
    def serialize_created_at(self, dt: Any, _info):
        if isinstance(dt, datetime):
            return SchemaCore.sync_timezone(dt).isoformat()
        return dt


class StickerHistoryPage(BaseModel):
    period_start: datetime = Field(..., description="현재 집계 기간 시작 시각")
    items: list[StickerHistoryItem] = Field(..., description="스티커 기록 목록")

    @field_serializer("period_start")
    def serialize_period_start(self, dt: Any, _info):
        if isinstance(dt, datetime):
            return SchemaCore.sync_timezone(dt).isoformat()
        return dt


async def _get_student_count() -> int:
    """
    전체 학생 수를 가져옵니다. 포인트 랭킹과 같은 캐시 Key를 사용합니다.

    Returns:
        int
    """
    key = Keys.Ranking.COUNT(type=UserType.student.value)
    cached = await client.redis.get(key)
    if cached is not None:
        return int(cached)

    async with client.session as session:
        query = select(func.count()).select_from(Users).where(col(Users.type) == UserType.student)
        count = (await session.execute(query)).scalar() or 0

    await client.redis.set(key, count)
    return count


def _ranking_search_condition(ranked: Subquery, q: str) -> ColumnElement[bool] | None:
    """
    `/search`와 같은 규칙으로 랭킹 서브쿼리에 적용할 검색 조건을 만듭니다.

    Args:
        ranked: 순위를 계산한 서브쿼리
        q: 공백을 제거하지 않은 검색어

    Returns:
        ColumnElement[bool] | None: 결과가 없는 검색어(4자 미만의 숫자)인 경우 None
    """
    q = q.replace(" ", "")
    if q.isdigit():
        # 학번은 4자이므로 4자 미만의 숫자는 결과가 없습니다.
        if len(q) < 4:
            return None
        return ranked.c.id == int(q)

    decomposed = client.normalize_and_decompose(q)
    matched_ids = select(UserSearch.user_id).where(col(UserSearch.value).like(f"%{decomposed}%"))
    return ranked.c.id.in_(matched_ids)


@router.post(
    "",
    operation_id="grant_sticker",
    response_model=ResponseModel[StickerBalance],
    responses={
        200: {"description": "스티커 지급 성공"},
        400: {"model": ErrorResponse, "description": "학생 또는 교사가 아닌 유저에게 지급 시도"},
        401: {"model": ErrorResponse, "description": "세션이 만료되었거나 유효하지 않음"},
        403: {"model": ErrorResponse, "description": "권한이 없음"},
        404: {"model": ErrorResponse, "description": "유저를 찾을 수 없음"},
        409: {"model": ErrorResponse, "description": f"이번 주 한도({STICKER_MAX}개) 초과"},
    },
    status_code=status.HTTP_200_OK,
    summary="스티커 지급",
    description=(
        f"학생 또는 교사에게 스티커를 1~{STICKER_MAX}개 지급합니다. "
        f"한 명이 이번 주(월요일 00:00 KST 이후)에 받을 수 있는 스티커는 {STICKER_MAX}개까지이며, "
        "보유 수와 순위는 집계 기간 동안 누적됩니다."
    ),
)
async def grant_sticker(data: StickerOperation, auth_data: LoginDep):
    user, _ = auth_data
    if not (user.has_permission(UserPermission.GIVE_STICKER) or user.has_permission(UserPermission.MANAGE_STICKER)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="권한이 없습니다.")

    try:
        result = await Sticker.grant(data.user_id, user, data.amount, memo=data.memo)
    except NotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except LimitExceeded as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    return ResponseModel(success=True, data=_balance(data.user_id, result))


@router.post(
    "/bulk",
    operation_id="grant_stickers",
    response_model=ResponseModel[StickerBulkResult],
    responses={
        200: {"description": "일괄 지급 처리 완료 (일부 또는 전부 실패해도 200이며 결과는 본문에 있음)"},
        401: {"model": ErrorResponse, "description": "세션이 만료되었거나 유효하지 않음"},
        403: {"model": ErrorResponse, "description": "권한이 없음"},
    },
    status_code=status.HTTP_200_OK,
    summary="스티커 일괄 지급",
    description=(
        f"여러 학생 또는 교사에게 스티커를 한 번에 지급합니다. (최대 {MAX_BULK_TARGETS}명) "
        "유저마다 따로 처리하며, 이번 주 남은 한도가 요청 수보다 적은 유저에게는 남은 한도만큼만 지급합니다. "
        "(실제 지급 수는 `granted`) 남은 한도가 없거나 찾을 수 없는 유저는 건너뛰고 `failed`에 이유를 담아 돌려줍니다."
    ),
)
async def grant_stickers(data: StickerBulkOperation, auth_data: LoginDep):
    user, _ = auth_data
    if not (user.has_permission(UserPermission.GIVE_STICKER) or user.has_permission(UserPermission.MANAGE_STICKER)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="권한이 없습니다.")

    results = await Sticker.grant_many(data.user_ids, user, data.amount, memo=data.memo)

    return ResponseModel(
        success=True,
        data=StickerBulkResult(
            succeeded=[
                StickerBulkGranted(**_balance(item.user_id, item.balance).model_dump(), granted=item.balance.changed)
                for item in results
                if item.balance is not None
            ],
            failed=[
                StickerBulkFailure(user_id=item.user_id, reason=item.reason or "알 수 없는 오류")
                for item in results
                if item.balance is None
            ],
        ),
    )


@router.post(
    "/revoke",
    operation_id="revoke_sticker",
    response_model=ResponseModel[StickerBalance],
    responses={
        200: {"description": "스티커 회수 성공"},
        400: {"model": ErrorResponse, "description": "학생 또는 교사가 아닌 유저"},
        401: {"model": ErrorResponse, "description": "세션이 만료되었거나 유효하지 않음"},
        403: {"model": ErrorResponse, "description": "권한이 없음"},
        404: {"model": ErrorResponse, "description": "유저를 찾을 수 없음"},
        409: {"model": ErrorResponse, "description": "보유 수보다 많이 회수 시도"},
    },
    status_code=status.HTTP_200_OK,
    summary="스티커 회수",
    description="유저의 스티커를 회수합니다. 현재 집계 기간 내 보유 수 이하로만 회수할 수 있습니다.",
)
async def revoke_sticker(data: StickerOperation, auth_data: LoginDep):
    user, _ = auth_data
    if not user.has_permission(UserPermission.MANAGE_STICKER):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="권한이 없습니다.")

    try:
        result = await Sticker.revoke(data.user_id, user, data.amount, memo=data.memo)
    except NotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Conflict as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    return ResponseModel(success=True, data=_balance(data.user_id, result))


@router.post(
    "/class",
    operation_id="give_sticker_to_class",
    response_model=ResponseModel[StickerBalance],
    responses={
        200: {"description": "학급 전달 성공"},
        401: {"model": ErrorResponse, "description": "세션이 만료되었거나 유효하지 않음"},
        403: {"model": ErrorResponse, "description": "권한이 없음"},
        404: {"model": ErrorResponse, "description": "해당 학급(학생)이 없음"},
        409: {"model": ErrorResponse, "description": "보유한 스티커가 부족함"},
    },
    status_code=status.HTTP_200_OK,
    summary="학급에 스티커 전달 (교사)",
    description="교사가 보유한 스티커를 원하는 학급에 전달합니다. 전달한 만큼 교사 보유 수가 줄고 학급 합계에 더해집니다.",
)
async def give_sticker_to_class(data: StickerClassOperation, auth_data: LoginDep):
    user, _ = auth_data
    if not user.has_permission(UserPermission.GIVE_CLASS_STICKER):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="권한이 없습니다.")

    try:
        result = await Sticker.give_to_class(user, data.grade, data.number, data.amount, memo=data.memo)
    except Conflict as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except NotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return ResponseModel(success=True, data=_balance(user.id, result))


@router.post(
    "/reset",
    operation_id="reset_stickers",
    responses={
        204: {"description": "스티커 초기화 성공"},
        401: {"model": ErrorResponse, "description": "세션이 만료되었거나 유효하지 않음"},
        403: {"model": ErrorResponse, "description": "권한이 없음"},
    },
    status_code=status.HTTP_204_NO_CONTENT,
    summary="스티커 수동 초기화",
    description="모든 유저의 현재 스티커 보유 수를 0으로 만듭니다. 기록은 삭제되지 않으며 새 집계 기간이 시작됩니다.",
)
async def reset_stickers(auth_data: LoginDep):
    user, _ = auth_data
    if not user.has_permission(UserPermission.MANAGE_STICKER):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="권한이 없습니다.")

    await Sticker.reset(user)


@router.get(
    "/me",
    operation_id="get_my_sticker_balance",
    response_model=ResponseModel[StickerBalance],
    responses={
        200: {"description": "내 스티커 보유 수 조회 성공"},
        401: {"model": ErrorResponse, "description": "세션이 만료되었거나 유효하지 않음"},
        403: {"model": ErrorResponse, "description": "권한이 없음"},
    },
    status_code=status.HTTP_200_OK,
    summary="내 스티커 보유 수 조회",
    description="현재 집계 기간 내 내 스티커 보유 수를 조회합니다. 학생 또는 교사가 아닌 경우 0을 반환합니다.",
)
async def get_my_sticker_balance(auth_data: LoginDep):
    user, _ = auth_data
    if not user.has_permission(UserPermission.VIEW_STICKER):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="권한이 없습니다.")

    if user.type in STICKER_TARGET_TYPES:
        result = await Sticker.get_balance(user.id)
    else:
        period_start = await Sticker.get_period_start()
        result = StickerCount(
            count=0, period_start=period_start, week_count=0, week_start=Sticker.get_week_start(period_start)
        )

    return ResponseModel(success=True, data=_balance(user.id, result))


@router.get(
    "/users/{user_id}",
    operation_id="get_user_sticker_balance",
    response_model=ResponseModel[StickerBalance],
    responses={
        200: {"description": "유저 스티커 보유 수 조회 성공"},
        401: {"model": ErrorResponse, "description": "세션이 만료되었거나 유효하지 않음"},
        403: {"model": ErrorResponse, "description": "권한이 없음"},
        404: {"model": ErrorResponse, "description": "유저를 찾을 수 없음"},
    },
    status_code=status.HTTP_200_OK,
    summary="특정 유저 스티커 보유 수 조회",
    description="지급 · 관리 권한이 있는 유저가 특정 유저의 현재 스티커 보유 수를 조회합니다.",
)
async def get_user_sticker_balance(user_id: int, auth_data: LoginDep):
    user, _ = auth_data
    if not (user.has_permission(UserPermission.GIVE_STICKER) or user.has_permission(UserPermission.MANAGE_STICKER)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="권한이 없습니다.")

    target = await client.get_user(user_id, cache=True)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="유저를 찾을 수 없습니다.")

    return ResponseModel(success=True, data=_balance(target.id, await Sticker.get_balance(target.id)))


@router.get(
    "/ranking",
    operation_id="get_sticker_ranking",
    response_model=ResponseModel[list[StickerRankingResponse]],
    responses={
        200: {"description": "스티커 개인 랭킹 조회 성공"},
        401: {"model": ErrorResponse, "description": "세션이 만료되었거나 유효하지 않음"},
        403: {"model": ErrorResponse, "description": "권한이 없음"},
    },
    status_code=status.HTTP_200_OK,
    summary="스티커 개인 랭킹 조회",
    description=(
        "현재 집계 기간 내 스티커 보유 수 기준 학생 랭킹을 조회합니다. "
        "`week_count`는 이번 주에 받은 수로, 화면에서 주간 한도 하트를 채우는 데 사용합니다. "
        "`q`로 이름(초성 포함) 또는 학번을 검색할 수 있으며, 검색 결과의 순위는 전체 기준 순위입니다."
    ),
)
async def get_sticker_ranking(
    auth_data: LoginDep,
    response: Response,
    q: str | None = Query(None, description="검색어 (이름 또는 학번)"),
    limit: int = Query(20, ge=1, le=MAX_PAGE_LIMIT, description=f"페이지 당 데이터 갯수 (최대 {MAX_PAGE_LIMIT})"),
    offset: int = Query(0, ge=0),
):
    user, _ = auth_data
    if not user.has_permission(UserPermission.VIEW_STICKER):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="권한이 없습니다.")

    q = (q or "").strip()
    period_start = await Sticker.get_period_start()
    week_start = Sticker.get_week_start(period_start)

    # 검색어가 없는 요청만 캐시합니다. (검색어마다 캐시하면 Key가 너무 많아짐)
    cache_key = None
    count = 0
    if not q:
        count = await _get_student_count()
        ver = await client.redis.get_version(Keys.Sticker.VERSION())
        cache_key = Keys.Sticker.RANKING(
            ver=ver,
            period=Sticker.period_key(period_start),
            week=Sticker.period_key(week_start),
            limit=limit,
            offset=offset,
        )
        cached = await client.redis.get(cache_key)
        if cached is not None:
            response.headers["X-MAX-PAGE"] = str(ceil(count / limit))
            response.headers["X-CACHED"] = "true"
            return ResponseModel(success=True, data=[StickerRankingResponse(**item) for item in cached])

    period_sum = (
        select(col(StickerHistory.user_id), func.sum(StickerHistory.amount).label("cnt"))
        .where(col(StickerHistory.created_at) >= period_start)
        .group_by(col(StickerHistory.user_id))
        .subquery()
    )
    sticker_count = func.coalesce(period_sum.c.cnt, 0)
    # 이번 주 받은 수 (하트 표시용). 학급 전달 기록은 교사 것이라 학생 랭킹에는 없지만 서비스와 같은 기준으로 제외합니다.
    week_sum = (
        select(col(StickerHistory.user_id), func.sum(StickerHistory.amount).label("cnt"))
        .where(col(StickerHistory.created_at) >= week_start, col(StickerHistory.class_grade).is_(None))
        .group_by(col(StickerHistory.user_id))
        .subquery()
    )
    # 검색 결과에서도 전체 기준 순위를 유지하기 위해 순위를 먼저 계산한 뒤 바깥에서 검색 조건을 적용합니다.
    ranked = (
        select(
            col(Users.id).label("id"),
            col(Users.name).label("name"),
            col(Users.grade).label("grade"),
            col(Users.number).label("number"),
            sticker_count.label("count"),
            func.coalesce(week_sum.c.cnt, 0).label("week_count"),
            func.dense_rank().over(order_by=sticker_count.desc()).label("rank"),
        )
        .outerjoin(period_sum, period_sum.c.user_id == Users.id)
        .outerjoin(week_sum, week_sum.c.user_id == Users.id)
        .where(col(Users.type) == UserType.student)
        .subquery()
    )

    base = select(ranked)
    if q:
        condition = _ranking_search_condition(ranked, q)
        if condition is None:
            response.headers["X-MAX-PAGE"] = "0"
            return ResponseModel(success=True, data=[])
        base = base.where(condition)

    async with client.session as session:
        if q:
            count = (await session.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0

        query = base.order_by(ranked.c.count.desc(), ranked.c.id.asc()).limit(limit).offset(offset)
        rows = (await session.execute(query)).all()

    rankings = [
        StickerRankingResponse(
            id=row.id,
            name=row.name,
            grade=row.grade,
            number=row.number,
            count=int(row.count),
            week_count=int(row.week_count),
            rank=int(row.rank),
        )
        for row in rows
    ]
    if cache_key is not None:
        await client.redis.set(cache_key, [item.model_dump() for item in rankings])

    response.headers["X-MAX-PAGE"] = str(ceil(count / limit))
    return ResponseModel(success=True, data=rankings)


@router.get(
    "/ranking/class",
    operation_id="get_sticker_class_ranking",
    response_model=ResponseModel[list[StickerClassRankingResponse]],
    responses={
        200: {"description": "스티커 학급 랭킹 조회 성공"},
        401: {"model": ErrorResponse, "description": "세션이 만료되었거나 유효하지 않음"},
        403: {"model": ErrorResponse, "description": "권한이 없음"},
    },
    status_code=status.HTTP_200_OK,
    summary="스티커 학급 랭킹 조회",
    description=(
        "학급별(학년, 반) 스티커 합계를 조회합니다. "
        "결과는 1학년 1반부터 학년, 반 순으로 정렬되며 `rank`는 합계 기준 순위입니다."
    ),
)
async def get_sticker_class_ranking(auth_data: LoginDep, response: Response):
    user, _ = auth_data
    if not user.has_permission(UserPermission.VIEW_STICKER):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="권한이 없습니다.")

    period_start = await Sticker.get_period_start()
    ver = await client.redis.get_version(Keys.Sticker.VERSION())
    cache_key = Keys.Sticker.CLASS_RANKING(ver=ver, period=Sticker.period_key(period_start))

    cached = await client.redis.get(cache_key)
    if cached is not None:
        response.headers["X-CACHED"] = "true"
        return ResponseModel(success=True, data=[StickerClassRankingResponse(**item) for item in cached])

    # 학급 학생들의 보유 합계
    student_query = (
        select(col(Users.grade), col(Users.number), func.coalesce(func.sum(StickerHistory.amount), 0).label("count"))
        .select_from(Users)
        .outerjoin(
            StickerHistory,
            and_(col(StickerHistory.user_id) == Users.id, col(StickerHistory.created_at) >= period_start),
        )
        .where(
            col(Users.type) == UserType.student,
            col(Users.grade).isnot(None),
            col(Users.number).isnot(None),
        )
        .group_by(col(Users.grade), col(Users.number))
        .order_by(col(Users.grade).asc(), col(Users.number).asc())
    )
    # 교사가 학급에 전달한 합계 (전달 기록은 교사 기준 음수이므로 부호를 뒤집어 더합니다)
    teacher_query = (
        select(
            col(StickerHistory.class_grade),
            col(StickerHistory.class_number),
            func.coalesce(func.sum(-col(StickerHistory.amount)), 0).label("count"),
        )
        .where(
            col(StickerHistory.class_grade).isnot(None),
            col(StickerHistory.class_number).isnot(None),
            col(StickerHistory.created_at) >= period_start,
        )
        .group_by(col(StickerHistory.class_grade), col(StickerHistory.class_number))
    )

    async with client.session as session:
        student_rows = (await session.execute(student_query)).all()
        teacher_rows = (await session.execute(teacher_query)).all()

    teacher_counts = {(row.class_grade, row.class_number): int(row.count) for row in teacher_rows}
    totals = [
        (row.grade, row.number, int(row.count) + teacher_counts.get((row.grade, row.number), 0)) for row in student_rows
    ]

    # 정렬은 학년, 반 순을 유지하고 순위만 합계 기준 dense rank로 계산합니다.
    rank_of = {total: index + 1 for index, total in enumerate(sorted({total for _, _, total in totals}, reverse=True))}
    result = [
        StickerClassRankingResponse(
            grade=grade,
            number=number,
            count=total,
            teacher_count=teacher_counts.get((grade, number), 0),
            rank=rank_of[total],
        )
        for grade, number, total in totals
    ]
    await client.redis.set(cache_key, [item.model_dump() for item in result])

    return ResponseModel(success=True, data=result)


@router.get(
    "/history",
    operation_id="get_sticker_history",
    response_model=ResponseModel[StickerHistoryPage],
    responses={
        200: {"description": "스티커 기록 조회 성공"},
        401: {"model": ErrorResponse, "description": "세션이 만료되었거나 유효하지 않음"},
        403: {"model": ErrorResponse, "description": "권한이 없음"},
    },
    status_code=status.HTTP_200_OK,
    summary="스티커 기록 조회 (관리자)",
    description=(
        "현재 집계 기간 내 스티커 지급 · 회수 · 학급 전달 기록을 최신순으로 조회합니다. "
        "`user_id`로 특정 유저의 기록만 조회할 수 있습니다."
    ),
)
async def get_sticker_history(
    auth_data: LoginDep,
    response: Response,
    user_id: int | None = Query(None, description="특정 유저의 기록만 조회"),
    limit: int = Query(20, ge=1, le=MAX_PAGE_LIMIT, description=f"페이지 당 데이터 갯수 (최대 {MAX_PAGE_LIMIT})"),
    offset: int = Query(0, ge=0),
):
    user, _ = auth_data
    if not user.has_permission(UserPermission.MANAGE_STICKER):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="권한이 없습니다.")

    period_start = await Sticker.get_period_start()
    conditions = [col(StickerHistory.created_at) >= period_start]
    if user_id is not None:
        conditions.append(col(StickerHistory.user_id) == user_id)

    target = aliased(Users)
    actor = aliased(Users)
    query = (
        select(
            StickerHistory,
            col(target.name).label("user_name"),
            col(target.type).label("user_type"),
            col(target.grade).label("grade"),
            col(target.number).label("number"),
            col(actor.name).label("actor_name"),
        )
        .outerjoin(target, col(target.id) == StickerHistory.user_id)
        .outerjoin(actor, col(actor.id) == StickerHistory.actor_id)
        .where(*conditions)
        .order_by(col(StickerHistory.created_at).desc(), col(StickerHistory.id).desc())
        .limit(limit)
        .offset(offset)
    )

    async with client.session as session:
        count_query = select(func.count()).select_from(StickerHistory).where(*conditions)
        count = (await session.execute(count_query)).scalar() or 0
        rows = (await session.execute(query)).all()

    items = [
        StickerHistoryItem(
            id=history.id,
            user_id=history.user_id,
            user_name=user_name,
            user_type=user_type,
            class_grade=history.class_grade,
            class_number=history.class_number,
            grade=grade,
            number=number,
            amount=history.amount,
            actor_id=history.actor_id,
            actor_name=actor_name,
            memo=history.memo,
            created_at=history.created_at,
        )
        for history, user_name, user_type, grade, number, actor_name in rows
    ]

    response.headers["X-MAX-PAGE"] = str(ceil(count / limit))
    return ResponseModel(success=True, data=StickerHistoryPage(period_start=period_start, items=items))


@router.delete(
    "/history/{history_id}",
    operation_id="delete_sticker_history",
    responses={
        204: {"description": "스티커 기록 취소 성공"},
        401: {"model": ErrorResponse, "description": "세션이 만료되었거나 유효하지 않음"},
        403: {"model": ErrorResponse, "description": "권한이 없음"},
        404: {"model": ErrorResponse, "description": "기록을 찾을 수 없음"},
        409: {"model": ErrorResponse, "description": "취소 시 대상 유저의 보유 수가 0 미만이 됨"},
    },
    status_code=status.HTTP_204_NO_CONTENT,
    summary="스티커 기록 취소 (관리자)",
    description=(
        "스티커 기록 하나를 삭제해 해당 변동을 없던 것으로 만듭니다. "
        "삭제 후 대상 유저의 현재 기간 보유 수가 0 미만이 되는 경우 거부됩니다."
    ),
)
async def delete_sticker_history(history_id: int, auth_data: LoginDep):
    user, _ = auth_data
    if not user.has_permission(UserPermission.MANAGE_STICKER):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="권한이 없습니다.")

    history = await client.get_sticker(history_id)
    if history is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="스티커 기록을 찾을 수 없습니다.")

    try:
        await history.cancel(user)
    except Conflict as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
