from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from sqlmodel import col, func, select

from app.schemas import StickerHistory, StickerReset, Users, UserType
from app.schemas.core import SchemaCore

from ..cache_events import on_sticker_history_deleted
from ..core import DatabaseCore, ServiceCore
from ..error import Conflict, NotFound
from ..redis_keys import Keys

if TYPE_CHECKING:
    from .user import User

    _Type = StickerHistory
else:
    _Type = object

STICKER_MAX = 3
"""한 명이 한 주 동안 받을 수 있는 최대 스티커 수 (보유 수가 아니라 이번 주에 지급받은 수 기준)"""

STICKER_TIMEZONE = ZoneInfo("Asia/Seoul")
"""집계 기간(매월 1일 00:00)과 주간 한도(월요일 00:00)의 기준 시각을 계산할 시간대. DB 시간대와 관계없이 학교 기준(KST)입니다."""

STICKER_TARGET_TYPES = (UserType.student, UserType.teacher)
"""스티커를 받을 수 있는 유저 타입"""


@dataclass
class StickerCount:
    count: int
    """집계 기간 내 보유 스티커 수"""
    period_start: datetime
    """집계 기간 시작 시각"""
    week_count: int
    """이번 주에 지급받은 스티커 수 (학급 전달 기록 제외, 회수는 반영)"""
    week_start: datetime
    """이번 주 한도 계산 시작 시각"""
    changed: int = 0
    """이번 처리로 실제 변동된 수량 (지급 +, 회수 · 학급 전달 -, 조회만 한 경우 0)"""


@dataclass
class StickerBulkItem:
    user_id: int
    """대상 유저 ID"""
    balance: StickerCount | None
    """지급 성공 시 지급 후 보유 수, 실패 시 None"""
    reason: str | None
    """지급 실패 사유, 성공 시 None"""


@dataclass
class StickerClassGrant:
    grade: int
    """대상 학년"""
    number: int
    """대상 반"""
    granted: int
    """이번 요청으로 지급한 수"""
    given_count: int
    """현재 집계 기간에 서비스 계정이 이 학급에 지급한 누적 수 (이번 지급 포함)"""
    period_start: datetime
    """집계 기간 시작 시각"""


class Sticker(ServiceCore[StickerHistory], _Type):
    """
    스티커 기록 서비스

    보유 수는 따로 저장하지 않고, 현재 집계 기간 내 `StickerHistory.amount` 합계로 계산합니다.
    집계 기간은 `max(이번 달 1일 00:00 KST, 가장 최근 수동 초기화 시각)`부터 시작합니다.
    지급 한도(`STICKER_MAX`)는 보유 수가 아니라 이번 주(`max(월요일 00:00 KST, 집계 기간 시작)`)에 지급받은 수를 기준으로 합니다.
    스티커 지급 · 회수 · 학급 전달 처리는 포인트와 마찬가지로 `User`의 `sticker_*` 메서드에서 합니다.
    관련된 Redis Key는 `app.core.redis_keys.Keys.Sticker`에 정의되어 있습니다.
    """

    @classmethod
    async def get_by_id(cls, history_id: int, **kwargs) -> Sticker | None:
        """
        ID를 기반으로 스티커 기록을 가져옵니다.

        Args:
            history_id: ID

        Returns:
            Sticker | None
        """
        return await cls._get_item(
            _id=history_id,
            wrapper_cls=cls,
            model_cls=StickerHistory,
            key=Keys.Sticker.ITEM(history_id=history_id),
            **kwargs,
        )

    @staticmethod
    async def get_period_start() -> datetime:
        """
        현재 집계 기간의 시작 시각을 DB 서버 시간대로 반환합니다.

        Returns:
            datetime: 이번 달 1일 00:00(KST)과 가장 최근 수동 초기화 시각 중 늦은 시각
        """
        now = SchemaCore.now().astimezone(STICKER_TIMEZONE)
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).astimezone(SchemaCore.timezone)

        async with DatabaseCore.session() as session:
            latest_reset = (await session.execute(select(func.max(StickerReset.reset_at)))).scalar()

        if latest_reset is not None:
            # DB에서 읽은 값은 시간대 정보가 없으므로 DB 서버 시간대를 붙여 비교합니다.
            start = max(start, SchemaCore.sync_timezone(latest_reset))
        return start

    @staticmethod
    def get_week_start(period_start: datetime, now: datetime | None = None) -> datetime:
        """
        이번 주 지급 한도를 계산할 시작 시각을 DB 서버 시간대로 반환합니다.

        Args:
            period_start: 현재 집계 기간 시작 시각
            now: 기준 시각 (생략 시 현재 시각, 검증용)

        Returns:
            datetime: 이번 주 월요일 00:00(KST)과 집계 기간 시작 중 늦은 시각
                (수동 초기화 뒤에는 다시 한도만큼 받을 수 있어야 하므로 기간 시작보다 앞으로 가지 않습니다)
        """
        now_kst = (now or SchemaCore.now()).astimezone(STICKER_TIMEZONE)
        monday = now_kst - timedelta(days=now_kst.weekday())
        week_start = monday.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(SchemaCore.timezone)
        return max(week_start, period_start)

    @staticmethod
    def period_key(period_start: datetime) -> str:
        """
        집계 기간 시작 시각을 캐시 Key에 쓸 문자열(`YYYYMMDDHHMMSS`, KST)로 바꿉니다.

        Args:
            period_start: 집계 기간 시작 시각

        Returns:
            str
        """
        return period_start.astimezone(STICKER_TIMEZONE).strftime("%Y%m%d%H%M%S")

    @staticmethod
    async def get_class_given_count(grade: int, number: int, period_start: datetime) -> int:
        """
        서비스 계정이 집계 기간 동안 학급에 직접 지급한 스티커 수를 계산합니다.
        학급 지급 기록은 서비스 계정 기준 음수로 저장되므로 부호를 뒤집어 더합니다.

        Args:
            grade: 학년
            number: 반
            period_start: 집계 기간 시작 시각

        Returns:
            int
        """
        query = (
            select(func.coalesce(func.sum(-col(StickerHistory.amount)), 0))
            .select_from(StickerHistory)
            .join(Users, col(Users.id) == StickerHistory.user_id)
            .where(
                col(Users.type) == UserType.service,
                col(StickerHistory.class_grade) == grade,
                col(StickerHistory.class_number) == number,
                col(StickerHistory.created_at) >= period_start,
            )
        )
        async with DatabaseCore.session() as session:
            result = await session.execute(query)
        return int(result.scalar() or 0)

    @staticmethod
    async def list_classes() -> list[tuple[int, int]]:
        """
        학생이 한 명 이상 있는 학급(학년, 반) 목록을 조회합니다.
        `ensure_class_exists`와 같은 기준이므로, 이 목록에 있는 학급에는 학급 전달 · 지급을 할 수 있습니다.

        Returns:
            list[tuple[int, int]]: 학년, 반 순으로 정렬된 (학년, 반) 목록
        """
        query = (
            select(col(Users.grade), col(Users.number))
            .where(
                col(Users.type) == UserType.student,
                col(Users.grade).isnot(None),
                col(Users.number).isnot(None),
            )
            .distinct()
            .order_by(col(Users.grade).asc(), col(Users.number).asc())
        )
        async with DatabaseCore.session() as session:
            rows = (await session.execute(query)).all()
        return [(int(row.grade), int(row.number)) for row in rows]

    @staticmethod
    async def ensure_class_exists(grade: int, number: int):
        """
        해당 학급에 학생이 한 명 이상 있는지 확인합니다.

        Args:
            grade: 학년
            number: 반

        Raises:
            ServiceError.NotFound: 해당 학급에 학생이 없는 경우 발생합니다.
        """
        query = (
            select(func.count())
            .select_from(Users)
            .where(
                col(Users.type) == UserType.student,
                col(Users.grade) == grade,
                col(Users.number) == number,
            )
        )
        async with DatabaseCore.session() as session:
            result = await session.execute(query)
        if not result.scalar():
            raise NotFound("해당 학급을 찾을 수 없습니다.")

    async def cancel(self, actor: User):
        """
        스티커 기록을 삭제해 해당 변동을 없던 것으로 만듭니다.

        Args:
            actor: 취소하는 유저

        Raises:
            ServiceError.Conflict: 현재 집계 기간의 지급(양수) 기록이고, 취소하면 대상 유저의 보유 수가 0 미만이 되는 경우 발생합니다.
        """
        from .user import User

        async with self.session as session:
            # 보유 수 계산과 기록 삭제 사이에 다른 요청이 끼어들지 않도록 대상 유저 행을 잠급니다.
            user = await User.get_by_id(self.user_id, lock=True)

            period_start = await self.get_period_start()
            # 이전 집계 기간의 기록은 현재 보유 수에 영향을 주지 않으므로 확인하지 않습니다.
            # 음수 기록(회수 · 학급 전달 · 학급 지급)을 지우면 보유 수가 늘어나므로 지급 기록만 확인합니다.
            # (서비스 계정의 학급 지급 기록만 있는 경우 보유 수가 음수라 모든 취소가 막히는 것을 막습니다)
            if user is not None and self.amount > 0 and SchemaCore.sync_timezone(self.created_at) >= period_start:
                held = await user.get_sticker_count(period_start)
                if held - self.amount < 0:
                    raise Conflict(f"이 기록을 취소하면 보유 수가 0 미만이 됩니다. (현재 {held}개)")

            history = await session.merge(self._payload)
            await session.delete(history)

        await on_sticker_history_deleted(self.id)
        self.logs.service_sticker.info(
            f"스티커 기록 취소 - ID {self.id} (유저 {self.user_id}, {self.amount:+d}, 처리 {actor.name}({actor.id}))"
        )
