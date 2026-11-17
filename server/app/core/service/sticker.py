from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from sqlmodel import col, func, select

from app.schemas import StickerHistory, StickerReset, Users, UserType
from app.schemas.core import SchemaCore

from ..cache_events import on_sticker_changed
from ..core import DatabaseCore, LoggerCore, ServiceCore
from ..error import Conflict, LimitExceeded, NotFound
from .user import User

if TYPE_CHECKING:
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


@dataclass
class StickerBulkItem:
    user_id: int
    """대상 유저 ID"""
    balance: StickerCount | None
    """지급 성공 시 지급 후 보유 수, 실패 시 None"""
    reason: str | None
    """지급 실패 사유, 성공 시 None"""


class Sticker(ServiceCore[StickerHistory], _Type):
    """
    스티커 기록 서비스

    보유 수는 따로 저장하지 않고, 현재 집계 기간 내 `StickerHistory.amount` 합계로 계산합니다.
    집계 기간은 `max(이번 달 1일 00:00 KST, 가장 최근 수동 초기화 시각)`부터 시작합니다.
    지급 한도(`STICKER_MAX`)는 보유 수가 아니라 이번 주(`max(월요일 00:00 KST, 집계 기간 시작)`)에 지급받은 수를 기준으로 합니다.
    관련된 Redis Key는 `app.core.redis_keys.Keys.Sticker`에 정의되어 있습니다.
    """

    @classmethod
    async def get_by_id(cls, history_id: int) -> Sticker | None:
        """
        ID로 스티커 기록을 가져옵니다.

        Args:
            history_id: 스티커 기록 ID

        Returns:
            Sticker | None
        """
        async with DatabaseCore.session() as session:
            payload = await session.get(StickerHistory, history_id)
        return cls(payload=payload)

    @classmethod
    async def get_period_start(cls) -> datetime:
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

    @classmethod
    async def get_week_count(cls, user_id: int, week_start: datetime) -> int:
        """
        유저가 이번 주에 지급받은 스티커 수를 계산합니다.
        학급 전달 기록은 교사가 받은 것이 아니므로 제외하고, 회수(음수)는 포함해 한도를 되돌립니다.

        Args:
            user_id: 유저 ID
            week_start: 주간 한도 계산 시작 시각

        Returns:
            int
        """
        query = select(func.coalesce(func.sum(StickerHistory.amount), 0)).where(
            col(StickerHistory.user_id) == user_id,
            col(StickerHistory.created_at) >= week_start,
            col(StickerHistory.class_grade).is_(None),
        )
        async with DatabaseCore.session() as session:
            result = await session.execute(query)
        return int(result.scalar() or 0)

    @classmethod
    async def get_balance(cls, user_id: int) -> StickerCount:
        """
        유저의 현재 보유 수와 이번 주 지급받은 수를 함께 계산합니다.

        Args:
            user_id: 유저 ID

        Returns:
            StickerCount
        """
        period_start = await cls.get_period_start()
        week_start = cls.get_week_start(period_start)
        return StickerCount(
            count=await cls.get_count(user_id, period_start),
            period_start=period_start,
            week_count=await cls.get_week_count(user_id, week_start),
            week_start=week_start,
        )

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

    @classmethod
    async def get_count(cls, user_id: int, period_start: datetime) -> int:
        """
        유저가 집계 기간 동안 보유한 스티커 수를 계산합니다.

        Args:
            user_id: 유저 ID
            period_start: 집계 기간 시작 시각

        Returns:
            int
        """
        query = select(func.coalesce(func.sum(StickerHistory.amount), 0)).where(
            col(StickerHistory.user_id) == user_id,
            col(StickerHistory.created_at) >= period_start,
        )
        async with DatabaseCore.session() as session:
            result = await session.execute(query)
        return int(result.scalar() or 0)

    @classmethod
    async def grant(cls, target_id: int, actor: User, amount: int, *, memo: str | None = None) -> StickerCount:
        """
        유저에게 스티커를 지급합니다.

        Args:
            target_id: 스티커를 받을 유저 ID
            actor: 지급하는 유저
            amount: 지급할 스티커 수
            memo: 메모

        Raises:
            ServiceError.NotFound: 대상 유저를 찾을 수 없는 경우 발생합니다.
            ValueError: 대상 유저가 학생 또는 교사가 아닌 경우 발생합니다.
            ServiceError.LimitExceeded: 이번 주에 지급받은 수가 `STICKER_MAX`를 넘는 경우 발생합니다.

        Returns:
            StickerCount: 지급 후 대상 유저의 보유 수와 집계 기간
        """
        return await cls._change(target_id, actor, amount, memo=memo)

    @classmethod
    async def grant_many(
        cls, user_ids: list[int], actor: User, amount: int, *, memo: str | None = None
    ) -> list[StickerBulkItem]:
        """
        여러 유저에게 스티커를 지급합니다. 유저마다 독립된 트랜잭션으로 처리하므로 일부만 성공할 수 있습니다.

        Args:
            user_ids: 스티커를 받을 유저 ID 목록 (중복은 한 번만 처리)
            actor: 지급하는 유저
            amount: 유저마다 지급할 스티커 수
            memo: 메모

        Returns:
            list[StickerBulkItem]: 유저별 처리 결과 (성공 시 balance, 실패 시 reason)
        """
        results: list[StickerBulkItem] = []
        for user_id in dict.fromkeys(user_ids):
            try:
                balance = await cls.grant(user_id, actor, amount, memo=memo)
            except (NotFound, ValueError, LimitExceeded) as e:
                results.append(StickerBulkItem(user_id=user_id, balance=None, reason=str(e)))
                continue
            results.append(StickerBulkItem(user_id=user_id, balance=balance, reason=None))

        succeeded = sum(1 for item in results if item.balance is not None)
        LoggerCore.service_sticker.info(
            f"스티커 일괄 지급 - 처리 {actor.name}({actor.id}) 성공 {succeeded}명 / 실패 {len(results) - succeeded}명 "
            f"(유저마다 {amount}개)"
        )
        return results

    @classmethod
    async def revoke(cls, target_id: int, actor: User, amount: int, *, memo: str | None = None) -> StickerCount:
        """
        유저의 스티커를 회수합니다.

        Args:
            target_id: 스티커를 회수할 유저 ID
            actor: 회수하는 유저
            amount: 회수할 스티커 수
            memo: 메모

        Raises:
            ServiceError.NotFound: 대상 유저를 찾을 수 없는 경우 발생합니다.
            ValueError: 대상 유저가 학생 또는 교사가 아닌 경우 발생합니다.
            ServiceError.Conflict: 보유 수보다 많이 회수하려는 경우 발생합니다.

        Returns:
            StickerCount: 회수 후 대상 유저의 보유 수와 집계 기간
        """
        return await cls._change(target_id, actor, -amount, memo=memo)

    @classmethod
    async def _change(cls, target_id: int, actor: User, changed: int, *, memo: str | None) -> StickerCount:
        """
        스티커 지급(changed > 0) 또는 회수(changed < 0)를 처리합니다.

        Raises:
            ServiceError.NotFound: 대상 유저를 찾을 수 없는 경우 발생합니다.
            ValueError: 대상 유저가 학생 또는 교사가 아닌 경우 발생합니다.
            ServiceError.LimitExceeded: 이번 주에 지급받은 수가 `STICKER_MAX`를 넘는 경우 발생합니다.
            ServiceError.Conflict: 보유 수보다 많이 회수하려는 경우 발생합니다.

        Returns:
            StickerCount: 처리 후 대상 유저의 보유 수와 집계 기간
        """
        async with DatabaseCore.session() as session:
            # 보유 수 계산과 기록 추가 사이에 다른 요청이 끼어들지 않도록 대상 유저 행을 잠급니다.
            target = await User.get_by_id(target_id, lock=True)
            if target is None:
                raise NotFound("유저를 찾을 수 없습니다.")
            if target.type not in STICKER_TARGET_TYPES:
                raise ValueError("스티커는 학생 또는 교사에게만 지급할 수 있습니다.")

            period_start = await cls.get_period_start()
            week_start = cls.get_week_start(period_start)
            held = await cls.get_count(target.id, period_start)
            week_count = await cls.get_week_count(target.id, week_start)
            after = held + changed

            # 지급 한도는 보유 수가 아니라 이번 주에 받은 수로 검사합니다. (보유 수는 기간 동안 누적)
            if changed > 0 and week_count + changed > STICKER_MAX:
                raise LimitExceeded(f"이번 주 한도({STICKER_MAX}개)를 넘을 수 없습니다. (이번 주 {week_count}개 받음)")
            if after < 0:
                raise Conflict(f"보유한 스티커보다 많이 회수할 수 없습니다. (현재 {held}개)")

            history = StickerHistory(user_id=target.id, amount=changed, actor_id=actor.id, memo=memo)
            session.add(history)
            await session.flush()

        await on_sticker_changed()

        action = "지급" if changed > 0 else "회수"
        LoggerCore.service_sticker.info(
            f"스티커 {action} - {target.name}({target.id}) {changed:+d} "
            f"(처리 {actor.name}({actor.id}), 보유 {held} -> {after}, 이번 주 {week_count} -> {week_count + changed}, "
            f"기록 ID {history.id})"
        )
        return StickerCount(
            count=after, period_start=period_start, week_count=week_count + changed, week_start=week_start
        )

    @classmethod
    async def give_to_class(
        cls, teacher: User, grade: int, number: int, amount: int, *, memo: str | None = None
    ) -> StickerCount:
        """
        교사가 보유한 스티커를 학급에 전달합니다.
        전달 기록은 교사의 보유 수에서 빠지는 음수 기록(`class_grade`, `class_number` 포함)으로 남습니다.

        Args:
            teacher: 전달하는 교사
            grade: 대상 학년
            number: 대상 반
            amount: 전달할 스티커 수
            memo: 메모

        Raises:
            ServiceError.Conflict: 보유한 스티커가 전달할 수보다 적은 경우 발생합니다.
            ServiceError.NotFound: 해당 학급에 학생이 없는 경우 발생합니다.

        Returns:
            StickerCount: 전달 후 교사의 보유 수와 집계 기간
        """
        async with DatabaseCore.session() as session:
            # 보유 수 계산과 기록 추가 사이에 다른 요청이 끼어들지 않도록 교사 행을 잠급니다.
            await User.get_by_id(teacher.id, lock=True)

            period_start = await cls.get_period_start()
            week_start = cls.get_week_start(period_start)
            held = await cls.get_count(teacher.id, period_start)
            if held < amount:
                raise Conflict(f"보유한 스티커가 부족합니다. (현재 {held}개)")

            class_size_query = (
                select(func.count())
                .select_from(Users)
                .where(
                    col(Users.type) == UserType.student,
                    col(Users.grade) == grade,
                    col(Users.number) == number,
                )
            )
            if not (await session.execute(class_size_query)).scalar():
                raise NotFound("해당 학급을 찾을 수 없습니다.")

            history = StickerHistory(
                user_id=teacher.id,
                amount=-amount,
                actor_id=teacher.id,
                memo=memo,
                class_grade=grade,
                class_number=number,
            )
            session.add(history)
            await session.flush()

        await on_sticker_changed()

        after = held - amount
        LoggerCore.service_sticker.info(
            f"스티커 학급 전달 - {teacher.name}({teacher.id}) -> {grade}학년 {number}반 {amount}개 "
            f"(보유 {held} -> {after}, 기록 ID {history.id})"
        )
        # 학급 전달은 교사가 받은 수에 영향을 주지 않으므로 주간 수는 그대로 조회해 돌려줍니다.
        return StickerCount(
            count=after,
            period_start=period_start,
            week_count=await cls.get_week_count(teacher.id, week_start),
            week_start=week_start,
        )

    @classmethod
    async def reset(cls, actor: User):
        """
        새 집계 기간을 시작해 모든 유저의 보유 수를 0으로 만듭니다. 기존 기록은 삭제하지 않습니다.

        Args:
            actor: 초기화하는 유저
        """
        async with DatabaseCore.session() as session:
            session.add(StickerReset(reset_by_id=actor.id))

        await on_sticker_changed()
        LoggerCore.service_sticker.info(f"스티커 수동 초기화 - 처리 {actor.name}({actor.id})")

    async def cancel(self, actor: User):
        """
        스티커 기록을 삭제해 해당 변동을 없던 것으로 만듭니다.

        Args:
            actor: 취소하는 유저

        Raises:
            ServiceError.Conflict: 현재 집계 기간의 기록이고, 취소하면 대상 유저의 보유 수가 0 미만이 되는 경우 발생합니다.
        """
        async with self.session as session:
            # 보유 수 계산과 기록 삭제 사이에 다른 요청이 끼어들지 않도록 대상 유저 행을 잠급니다.
            await User.get_by_id(self.user_id, lock=True)

            period_start = await self.get_period_start()
            # 이전 집계 기간의 기록은 현재 보유 수에 영향을 주지 않으므로 확인하지 않습니다.
            if SchemaCore.sync_timezone(self.created_at) >= period_start:
                held = await self.get_count(self.user_id, period_start)
                if held - self.amount < 0:
                    raise Conflict(f"이 기록을 취소하면 보유 수가 0 미만이 됩니다. (현재 {held}개)")

            history = await session.merge(self._payload)
            await session.delete(history)

        await on_sticker_changed()
        self.logs.service_sticker.info(
            f"스티커 기록 취소 - ID {self.id} (유저 {self.user_id}, {self.amount:+d}, 처리 {actor.name}({actor.id}))"
        )
