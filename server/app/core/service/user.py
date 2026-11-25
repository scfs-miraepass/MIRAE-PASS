from datetime import datetime
from typing import TYPE_CHECKING

from app.schemas import (
    PointHistory,
    PointHistoryType,
    PollOperation,
    PostContent,
    Posts,
    Quests,
    StickerHistory,
    StickerReset,
    UserPermission,
    Users,
    UserType,
    KaraokeMembers,
    KaraokePartis,
    Karaokes,
)

from sqlmodel import col, func, select

from ..cache_events import (
    on_point_changed,
    on_post_changed,
    on_quest_changed,
    on_sticker_changed,
    on_user_cache_changed,
    on_user_profile_changed,
)
from ..core import ServiceCore
from ..error import Conflict, Forbidden, LimitExceeded
from ..redis_keys import Keys
from ..security import get_password_hash
from ..sessions import revoke_user_sessions
from .history import History
from .post import Post
from .quest import Quest
from .sticker import STICKER_MAX, STICKER_TARGET_TYPES, Sticker, StickerBulkItem, StickerClassGrant, StickerCount

if TYPE_CHECKING:
    _Type = Users
    from .karaoke.karaoke import Karaoke
    from .karaoke.member import KaraokeMember
    from .karaoke.party import KaraokeParty
else:
    _Type = object


USER_CACHE_EXCLUDE = frozenset({"password", "kiosk_password"})
"""유저 캐시(`Keys.User.ITEM`)에 저장하지 않는 필드"""


class User(ServiceCore[Users], _Type):
    if TYPE_CHECKING:
        # DB에서 불러온 유저만 감싸므로 id는 항상 존재합니다. (모델의 `int | None`은 INSERT 전 상태를 위한 타입)
        id: int

    def __getattribute__(self, name):
        # 캐시에서 불러온 유저는 비밀번호 해시를 갖고 있지 않습니다.
        # 이 경우 password가 None(비밀번호 미설정)으로 잘못 읽히지 않도록 접근 자체를 막습니다.
        payload_dict = super().__getattribute__("_payload").__dict__
        if name in ["password", "kiosk_password"] and (
            "password" not in payload_dict or "kiosk_password" not in payload_dict
        ):
            raise RuntimeError("캐시에서 불러온 유저에는 비밀번호가 없습니다. cache=False로 다시 조회해야 합니다.")
        return super().__getattribute__(name)

    @classmethod
    async def get_by_id(cls, user_id: int, **kwargs) -> User | None:
        """
        ID를 기반으로 사용자를 가져옵니다.

        Args:
            user_id: ID

        Returns:
            User | None
        """
        return await cls._get_item(
            _id=user_id,
            wrapper_cls=cls,
            model_cls=Users,
            key=Keys.User.ITEM(user_id=user_id),
            cache_exclude=USER_CACHE_EXCLUDE,
            **kwargs,
        )

    @property
    def permission(self) -> UserPermission:
        return UserPermission(self.permissions)

    async def update_password(self, _new: str | None):
        """
        사용자의 비밀번호를 업데이트 합니다.
        비밀번호가 변경되면 해당 사용자의 모든 로그인 세션이 종료됩니다.

        Args:
            _new: 새로운 비밀번호, None의 경우 초기 비밀번호 셋팅 상태로 설정합니다.
        """
        if isinstance(_new, str):
            self.logs.service.info(f"{self.name}({self.id})님의 비밀번호가 변경되었습니다.")
        else:
            self.logs.service.info(f"{self.name}({self.id})님의 비밀번호를 초기화했습니다.")
        async with self.session as session:
            user = await session.merge(self._payload)
            user.password = get_password_hash(_new) if isinstance(_new, str) else None
        self._payload = user
        await on_user_cache_changed(self.id)
        await revoke_user_sessions(self.id)

    async def update_kiosk_password(self, _new: str | None):
        """
        사용자의 키오스크 결재용 비밀번호를 업데이트 합니다.

        Args:
            _new: 새로운 비밀번호, None인 경우 비밀번호 설정이 되지 않은 것을 뜻하며 키오스크를 이용할 수 없습니다.

        Raises:
            ValueError: 설정하려는 비밀번호가 6자의 숫자가 아닌 경우 발생합니다.
        """

        if _new is not None and (len(_new) != 6 or not _new.isdecimal()):
            raise ValueError("키오스크 비밀번호는 6자의 숫자만 가능합니다.")

        if isinstance(_new, str):
            self.logs.service.info(f"{self.name}({self.id})님의 키오스크 결재용 비밀번호가 변경되었습니다.")
        else:
            self.logs.service.info(f"{self.name}({self.id})님의 키오스크 결재용 비밀번호가 제거되었습니다.")
        async with self.session as session:
            user = await session.merge(self._payload)
            user.kiosk_password = get_password_hash(str(_new)) if isinstance(_new, str) else None
        self._payload = user
        await on_user_cache_changed(self.id)

    async def create_history(
        self,
        changed: int,
        reason: str,
        *,
        memo: str | None = None,
        type: PointHistoryType = PointHistoryType.etc,
    ) -> History:
        """
        포인트 기록을 생성합니다.

        Args:
            changed: 변경된 포인트를 뜻합니다. 양수와 음수를 통해 입금및 출금이 처리 됩니다.
            reason: 포인트가 변경된 주 된 이유
            memo: 포인트를 처리한 유저가 입력하거나, 시스템의 의해서 추가적으로 확인 할 수 있는 이유
            type: 포인트가 변경된 종류 입니다.

        Returns:
            History
        """
        async with self.session as session:
            obj = PointHistory(
                user_id=self.id,
                changed_amount=changed,
                reason=reason,
                memo=memo,
                type=type,
            )
            session.add(obj)
            await session.flush()

        self.logs.service_point.debug(
            f"포인트 기록 생성 - ID {obj.id} ({reason[:10] + '...' if len(reason) > 10 else reason})"
        )
        return History(payload=obj)

    async def point_grant(
        self,
        amount: int,
        *,
        reason: str,
        memo: str | None = None,
        type: PointHistoryType | None = None,
        no_total: bool = False,
    ):
        """
        포인트를 지급합니다.

        Args:
            amount: 지급하려는 포인트
            reason: 포인트를 지급하는 이유
            memo: 포인트를 지급하는 추가적인 이유
            type: 포인트를 지급하는 이유의 카테고리(종류)
            no_total: 누적 포인트(Users.total_point)에 포함시키지 않도록 합니다.
        """
        if type is None:
            type = PointHistoryType.etc

        async with self.session as session:
            user = await session.merge(self._payload)
            before_total = user.total_point
            user.point += amount
            if no_total:
                user.total_point = before_total

            history = await self.create_history(changed=amount, reason=reason, memo=memo, type=type)

        await on_point_changed(self.id, user.type)

        self.logs.service_point.info(f"포인트 지급 - {self.name}({self.id}) +{amount} (기록 ID {history.id})")
        self._payload = user

    async def point_deduct(
        self,
        amount: int,
        *,
        reason: str,
        memo: str | None = None,
        type: PointHistoryType | None = None,
    ):
        """
        포인트를 차감합니다.

        Args:
            amount: 차감하려는 포인트
            reason: 포인트를 차감하는 이유
            memo: 포인트를 차감하는 추가적인 이유
            type: 포인트를 차감하는 이유의 카테고리(종류)

        Raises:
            ValueError: 보유중인 포인트가 부족할 경우 발생합니다.
        """
        if self.point < amount:
            raise ValueError("Insufficient points. Points cannot be less than 0.")

        if type is None:
            type = PointHistoryType.etc

        async with self.session as session:
            user = await session.merge(self._payload)
            user.point -= amount

            history = await self.create_history(changed=(amount * -1), reason=reason, memo=memo, type=type)

        await on_point_changed(self.id, user.type)

        self.logs.service_point.info(f"포인트 차감 - {self.name}({self.id}) +{amount} (기록 ID {history.id})")
        self._payload = user

    async def get_sticker_count(self, period_start: datetime) -> int:
        """
        집계 기간 동안 보유한 스티커 수를 계산합니다.

        Args:
            period_start: 집계 기간 시작 시각

        Returns:
            int
        """
        query = select(func.coalesce(func.sum(StickerHistory.amount), 0)).where(
            col(StickerHistory.user_id) == self.id,
            col(StickerHistory.created_at) >= period_start,
        )
        async with self.session as session:
            result = await session.execute(query)
        return int(result.scalar() or 0)

    async def get_sticker_week_count(self, week_start: datetime) -> int:
        """
        이번 주에 지급받은 스티커 수를 계산합니다.
        학급 전달 기록은 교사가 받은 것이 아니므로 제외하고, 회수(음수)는 포함해 한도를 되돌립니다.

        Args:
            week_start: 주간 한도 계산 시작 시각

        Returns:
            int
        """
        query = select(func.coalesce(func.sum(StickerHistory.amount), 0)).where(
            col(StickerHistory.user_id) == self.id,
            col(StickerHistory.created_at) >= week_start,
            col(StickerHistory.class_grade).is_(None),
        )
        async with self.session as session:
            result = await session.execute(query)
        return int(result.scalar() or 0)

    async def get_sticker_balance(self) -> StickerCount:
        """
        현재 스티커 보유 수와 이번 주 지급받은 수를 함께 계산합니다.

        Returns:
            StickerCount
        """
        period_start = await Sticker.get_period_start()
        week_start = Sticker.get_week_start(period_start)
        return StickerCount(
            count=await self.get_sticker_count(period_start),
            period_start=period_start,
            week_count=await self.get_sticker_week_count(week_start),
            week_start=week_start,
        )

    async def sticker_grant(self, target: User, amount: int, *, memo: str | None = None) -> StickerCount:
        """
        유저에게 스티커를 지급합니다.

        Args:
            target: 스티커를 받을 유저
            amount: 지급할 스티커 수
            memo: 메모

        Raises:
            ValueError: 대상 유저가 학생 또는 교사가 아닌 경우 발생합니다.
            ServiceError.LimitExceeded: 대상 유저가 이번 주에 지급받은 수가 `STICKER_MAX`를 넘는 경우 발생합니다.

        Returns:
            StickerCount: 지급 후 대상 유저의 보유 수와 집계 기간
        """
        return await self._sticker_change(target, amount, memo=memo)

    async def sticker_grant_many(
        self, user_ids: list[int], amount: int, *, memo: str | None = None
    ) -> list[StickerBulkItem]:
        """
        여러 유저에게 스티커를 지급합니다. 유저마다 독립된 트랜잭션으로 처리하므로 일부만 성공할 수 있습니다.
        이번 주 남은 한도가 요청 수보다 적은 유저에게는 남은 한도만큼만 지급하고, 남은 한도가 없으면 실패로 기록합니다.

        Args:
            user_ids: 스티커를 받을 유저 ID 목록 (중복은 한 번만 처리)
            amount: 유저마다 지급할 최대 스티커 수
            memo: 메모

        Returns:
            list[StickerBulkItem]: 유저별 처리 결과 (성공 시 balance와 실제 지급 수 `balance.changed`, 실패 시 reason)
        """
        results: list[StickerBulkItem] = []
        for user_id in dict.fromkeys(user_ids):
            target = await User.get_by_id(user_id)
            if target is None:
                results.append(StickerBulkItem(user_id=user_id, balance=None, reason="유저를 찾을 수 없습니다."))
                continue

            try:
                balance = await self._sticker_change(target, amount, memo=memo, clamp_to_limit=True)
            except (ValueError, LimitExceeded) as e:
                results.append(StickerBulkItem(user_id=user_id, balance=None, reason=str(e)))
                continue
            results.append(StickerBulkItem(user_id=user_id, balance=balance, reason=None))

        succeeded = sum(1 for item in results if item.balance is not None)
        clamped = sum(1 for item in results if item.balance is not None and item.balance.changed < amount)
        self.logs.service_sticker.info(
            f"스티커 일괄 지급 - 처리 {self.name}({self.id}) 성공 {succeeded}명(한도로 줄어든 {clamped}명) / "
            f"실패 {len(results) - succeeded}명 (요청 유저마다 {amount}개)"
        )
        return results

    async def sticker_revoke(self, target: User, amount: int, *, memo: str | None = None) -> StickerCount:
        """
        유저의 스티커를 회수합니다.

        Args:
            target: 스티커를 회수할 유저
            amount: 회수할 스티커 수
            memo: 메모

        Raises:
            ValueError: 대상 유저가 학생 또는 교사가 아닌 경우 발생합니다.
            ServiceError.Conflict: 대상 유저의 보유 수보다 많이 회수하려는 경우 발생합니다.

        Returns:
            StickerCount: 회수 후 대상 유저의 보유 수와 집계 기간
        """
        return await self._sticker_change(target, -amount, memo=memo)

    async def _sticker_change(
        self, target: User, changed: int, *, memo: str | None, clamp_to_limit: bool = False
    ) -> StickerCount:
        """
        유저에게 스티커 지급(changed > 0) 또는 회수(changed < 0)를 처리합니다.

        Args:
            target: 대상 유저
            changed: 변동 수량
            memo: 메모
            clamp_to_limit: True면 지급 시 이번 주 남은 한도까지만 줄여서 지급합니다. (일괄 지급용)
                남은 한도가 없으면 그대로 `LimitExceeded`가 발생합니다.

        Raises:
            ValueError: 대상 유저가 학생 또는 교사가 아닌 경우 발생합니다.
            ServiceError.LimitExceeded: 대상 유저가 이번 주에 지급받은 수가 `STICKER_MAX`를 넘는 경우 발생합니다.
            ServiceError.Conflict: 대상 유저의 보유 수보다 많이 회수하려는 경우 발생합니다.

        Returns:
            StickerCount: 처리 후 대상 유저의 보유 수와 집계 기간, 실제 변동 수량(`changed`)
        """
        if target.type not in STICKER_TARGET_TYPES:
            raise ValueError("스티커는 학생 또는 교사에게만 지급할 수 있습니다.")

        async with self.session as session:
            # 보유 수 계산과 기록 추가 사이에 다른 요청이 끼어들지 않도록 대상 유저 행을 잠급니다.
            await User.get_by_id(target.id, lock=True)

            period_start = await Sticker.get_period_start()
            week_start = Sticker.get_week_start(period_start)
            held = await target.get_sticker_count(period_start)
            week_count = await target.get_sticker_week_count(week_start)

            # 지급 한도는 보유 수가 아니라 이번 주에 받은 수로 검사합니다. (보유 수는 기간 동안 누적)
            if changed > 0 and week_count + changed > STICKER_MAX:
                remaining = STICKER_MAX - week_count
                if not clamp_to_limit or remaining <= 0:
                    raise LimitExceeded(
                        f"이번 주 한도({STICKER_MAX}개)를 넘을 수 없습니다. (이번 주 {week_count}개 받음)"
                    )
                # 일괄 지급: 요청 수 대신 남은 한도만큼만 지급합니다. 잠금 안에서 계산하므로 동시 요청에도 한도를 넘지 않습니다.
                changed = remaining
            after = held + changed

            if after < 0:
                raise Conflict(f"보유한 스티커보다 많이 회수할 수 없습니다. (현재 {held}개)")

            history = StickerHistory(user_id=target.id, amount=changed, actor_id=self.id, memo=memo)
            session.add(history)
            await session.flush()

        await on_sticker_changed()

        action = "지급" if changed > 0 else "회수"
        self.logs.service_sticker.info(
            f"스티커 {action} - {target.name}({target.id}) {changed:+d} "
            f"(처리 {self.name}({self.id}), 보유 {held} -> {after}, 이번 주 {week_count} -> {week_count + changed}, "
            f"기록 ID {history.id})"
        )
        return StickerCount(
            count=after,
            period_start=period_start,
            week_count=week_count + changed,
            week_start=week_start,
            changed=changed,
        )

    async def sticker_give_to_class(
        self, grade: int, number: int, amount: int, *, memo: str | None = None
    ) -> StickerCount:
        """
        **[교사 전용]**
        보유한 스티커를 학급에 전달합니다.
        전달 기록은 교사의 보유 수에서 빠지는 음수 기록(`class_grade`, `class_number` 포함)으로 남습니다.

        Args:
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
        async with self.session as session:
            # 보유 수 계산과 기록 추가 사이에 다른 요청이 끼어들지 않도록 교사 행을 잠급니다.
            await User.get_by_id(self.id, lock=True)

            period_start = await Sticker.get_period_start()
            week_start = Sticker.get_week_start(period_start)
            held = await self.get_sticker_count(period_start)
            if held < amount:
                raise Conflict(f"보유한 스티커가 부족합니다. (현재 {held}개)")

            await Sticker.ensure_class_exists(grade, number)

            history = StickerHistory(
                user_id=self.id,
                amount=-amount,
                actor_id=self.id,
                memo=memo,
                class_grade=grade,
                class_number=number,
            )
            session.add(history)
            await session.flush()

        await on_sticker_changed()

        after = held - amount
        self.logs.service_sticker.info(
            f"스티커 학급 전달 - {self.name}({self.id}) -> {grade}학년 {number}반 {amount}개 "
            f"(보유 {held} -> {after}, 기록 ID {history.id})"
        )
        # 학급 전달은 교사가 받은 수에 영향을 주지 않으므로 주간 수는 그대로 조회해 돌려줍니다.
        return StickerCount(
            count=after,
            period_start=period_start,
            week_count=await self.get_sticker_week_count(week_start),
            week_start=week_start,
        )

    async def sticker_grant_to_class(
        self, grade: int, number: int, amount: int, *, memo: str | None = None
    ) -> StickerClassGrant:
        """
        **[서비스 계정 전용]**
        학급에 스티커를 직접 지급합니다.
        학생 개인의 보유 수는 바뀌지 않고 학급 순위 합계에만 더해집니다.
        기록은 교사의 학급 전달과 같은 형태(서비스 계정 기준 음수, `class_grade`, `class_number` 포함)로 남기며,
        서비스 계정은 보유 수를 쓰지 않으므로 보유 수 확인과 주간 한도 검사를 하지 않습니다.

        Args:
            grade: 대상 학년
            number: 대상 반
            amount: 지급할 스티커 수
            memo: 메모

        Raises:
            ValueError: 유저가 서비스 계정이 아닌 경우 발생합니다.
            ServiceError.NotFound: 해당 학급에 학생이 없는 경우 발생합니다.

        Returns:
            StickerClassGrant: 지급 결과와 이 학급에 지급한 누적 수
        """
        if self.type != UserType.service:
            raise ValueError("학급 스티커 지급은 서비스 계정만 할 수 있습니다.")

        async with self.session as session:
            period_start = await Sticker.get_period_start()
            await Sticker.ensure_class_exists(grade, number)

            history = StickerHistory(
                user_id=self.id,
                amount=-amount,
                actor_id=self.id,
                memo=memo,
                class_grade=grade,
                class_number=number,
            )
            session.add(history)
            await session.flush()

        await on_sticker_changed()

        self.logs.service_sticker.info(
            f"스티커 학급 지급 - {self.name}({self.id}) -> {grade}학년 {number}반 {amount}개 (기록 ID {history.id})"
        )
        return StickerClassGrant(
            grade=grade,
            number=number,
            granted=amount,
            given_count=await Sticker.get_class_given_count(grade, number, period_start),
            period_start=period_start,
        )

    async def sticker_reset(self):
        """
        새 집계 기간을 시작해 모든 유저의 스티커 보유 수를 0으로 만듭니다. 기존 기록은 삭제하지 않습니다.
        """
        async with self.session as session:
            session.add(StickerReset(reset_by_id=self.id))

        await on_sticker_changed()
        self.logs.service_sticker.info(f"스티커 수동 초기화 - 처리 {self.name}({self.id})")

    async def create_post(self, *, title: str, content: dict, poll: PollOperation | None = None) -> Post:
        """
        게시글을 생성합니다.

        Args:
            title: 게시글의 제목
            content: 게시글의 본문 데이터
            poll: 함께 만들 설문 (없으면 설문 없이 생성)

        Returns:
            Post
        """
        async with self.session as session:
            obj = Posts(title=title, author_id=self.id)
            obj.content = PostContent(data=content)

            session.add(obj)
            await session.flush()

            # 설문이 빠진 공지가 남지 않도록 게시글과 같은 트랜잭션에서 만듭니다.
            if poll is not None:
                await Post.add_poll(session, obj.id, poll)

        await on_post_changed(count=True)

        self.logs.service_post.info(
            f"게시글 생성 - ID {obj.id} ({obj.title[:10] + '...' if len(obj.title) > 10 else obj.title}) By. {self.name}({self.id})"
        )
        return Post(payload=obj)

    async def create_quest(
        self,
        *,
        title: str,
        description: str,
        reward: int,
        end_date: datetime,
        max_repeat: int = 1,
    ) -> Quest:
        """
        **[교사 전용]**
        퀘스트를 생성합니다.

        Args:
            title: 퀘스트의 제목
            description: 퀘스트의 내용
            reward: 퀘스트 완료시 지급할 포인트
            end_date: 퀘스트 모집 마감일자
            max_repeat: 퀘스트 중복 참가 횟수

        Raises:
           ServiceError.Forbidden: 사용자가 교사 또는 관리자가 아닐경우 발생합니다.

        Returns:
            Quest
        """
        if not self.is_admin and self.type != UserType.teacher:
            raise Forbidden("Quest create is for teachers only")

        async with self.session as session:
            obj = Quests(
                title=title,
                description=description,
                reward=reward,
                end_date=end_date,
                max_repeat=max_repeat,
                created_by_teacher_id=self.id,
            )

            session.add(obj)
            await session.flush()
        await on_quest_changed()

        self.logs.service_quest.info(
            f"퀘스트 생성 - {self.id}({self.name}) 생성. ID {obj.id}({title[:10] if len(title) > 10 else title})"
        )
        return Quest(payload=obj)

    def has_permission(self, perm: UserPermission | int) -> bool:
        """
        권한을 소유중인지 확인합니다.

        Args:
            perm: 추가하려는 권한

        Returns:
            Bool
        """
        if isinstance(perm, int):
            perm = UserPermission(perm)
        return perm in self.permission

    async def add_permission(self, perm: UserPermission | int):
        """
        권한을 추가합니다.

        Args:
            perm: 추가하려는 권한

        Raises:
            ValueError: 추가하려는 권한이 이미 사용자에게 있는 경우 발생합니다.
        """
        if isinstance(perm, int):
            perm = UserPermission(perm)
        if self.has_permission(perm):
            raise ValueError("already have permission")

        async with self.session as session:
            user = await session.merge(self._payload)
            user.permissions = (self.permission | perm).value

        self._payload = user
        await on_user_profile_changed(self.id, user.type)

        self.logs.service.info(f"{self.id}({self.name})의 권한을 추가했습니다. (+{perm.name})")

    async def remove_permission(self, perm: UserPermission | int):
        """
        권한을 제거합니다.

        Args:
            perm: 제거하려는 권한

        Raises:
            ValueError: 제거하려는 권한이 사용자에게 없는 경우 발생합니다.
        """
        if isinstance(perm, int):
            perm = UserPermission(perm)
        if not self.has_permission(perm):
            raise ValueError("not have permission")

        async with self.session as session:
            user = await session.merge(self._payload)
            user.permissions = (self.permission & ~perm).value

        self._payload = user
        await on_user_profile_changed(self.id, user.type)

        self.logs.service.info(f"{self.id}({self.name})의 권한을 제거했습니다. (-{perm.name})")

    async def get_pending_karaokes(self) -> list["Karaoke"]:
        """
        현재 초대되어 수락 또는 거절 대기중인 노래방 예약(Karaokes) 목록을 가져옵니다.

        Returns:
            list[Karaoke]
        """
        from app.core.service.karaoke.karaoke import Karaoke

        async with self.session as session:
            query = (
                select(Karaokes)
                .join(KaraokePartis, col(Karaokes.id) == KaraokePartis.auction_id)
                .join(KaraokeMembers, col(KaraokePartis.id) == KaraokeMembers.party_id)
                .where(KaraokeMembers.user_id == self.id, KaraokeMembers.pending == True)
            )
            exc = await session.execute(query)
            payload = exc.scalars().all()

        return [Karaoke(payload=p) for p in payload]

    async def get_karaoke_member(self, party_id: int) -> "KaraokeMember | None":
        """
        특정 파티에 대한 자기 자신의 KaraokeMember 정보를 가져옵니다.

        Args:
            party_id: 조회할 파티의 고유 ID

        Returns:
            KaraokeMember | None
        """
        if self.id is None:
            raise RuntimeError()
        from app.core.service.karaoke.member import KaraokeMember

        return await KaraokeMember.get_member(party_id=party_id, user_id=self.id)

    async def get_party(self, karaoke: "Karaoke", *, cache: bool = False) -> "KaraokeParty | None":
        """
        유저가 해당 노래방 예약 경매에서 참여하거나, 리더로 있는 노래방 파티를 가져옵니다.

        Args:
            karaoke: 가져오려는 노래방 예약 경매
            cache: 파티 데이터 캐시 사용 여부 (조회 전용 경로에서만 사용)

        Returns:
            KaraokeParty | None
        """
        from .karaoke.party import KaraokeParty

        cache_key = Keys.Karaoke.USER_PARTY(karaoke_id=karaoke.id, user_id=self.id)
        cached = await self.redis.get(cache_key)
        if cached:
            party = await KaraokeParty.get_by_id(cached, cache=cache)
            return party

        async with self.session as session:
            query = (
                select(KaraokePartis)
                .join(KaraokeMembers, isouter=True)
                .where(
                    KaraokePartis.auction_id == karaoke.id,
                    KaraokePartis.dispersed == False,
                    (KaraokePartis.leader_id == self.id) | (KaraokeMembers.user_id == self.id),
                )
            )
            exc = await session.execute(query)
            payload: KaraokePartis | None = exc.scalar_one_or_none()

        if payload is None:
            return None

        await self.redis.set(cache_key, payload.id)
        return KaraokeParty(payload)
