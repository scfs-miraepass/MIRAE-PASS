import asyncio
from collections.abc import Coroutine
from contextvars import Context
from functools import cache
from typing import Any

from py_vapid import Vapid02, b64urlencode
from pywebpush import WebPushException, webpush_async
from sqlalchemy import delete, event, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlmodel import col, select

from app.schemas import NotificationSend, NotificationTargetType, PushMessage, PushSubscriptions, Users, UserType

from ..config import settings
from ..core import BaseCore
from ..loggers import LoggerCore

PUSH_TTL_SECONDS = 24 * 60 * 60
"""기기가 꺼져 있을 때 푸시 서비스가 알림을 보관하는 시간"""

PUSH_TIMEOUT_SECONDS = 10
PUSH_CONCURRENCY = 20
"""동시에 보내는 푸시 수"""

EXPIRED_STATUS_CODES = (404, 410)
"""구독이 만료 · 해제되었다는 푸시 서비스 응답. 이 응답을 받으면 구독을 지웁니다."""

_PENDING_KEY = "pending_push_messages"
_background_tasks: set[asyncio.Task] = set()


def spawn_background(coroutine: Coroutine[Any, Any, Any]) -> None:
    """
    응답과 별개로 백그라운드에서 코루틴을 실행합니다.

    빈 Context에서 실행해, 요청 중인 DB 세션(`DatabaseCore._session_context`)을 이어받지 않고 새 세션을 열게 합니다.
    작업이 끝나기 전에 가비지 컬렉션되지 않도록 참조를 보관합니다.
    """
    task = asyncio.get_running_loop().create_task(coroutine, context=Context())
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


def point_message(amount: int, reason: str) -> PushMessage:
    """
    포인트 지급(양수) · 차감(음수) 알림 메시지를 만듭니다.

    Args:
        amount: 변동량 (지급 양수, 차감 음수)
        reason: 포인트 기록의 사유

    Returns:
        PushMessage
    """
    title = "포인트 지급" if amount > 0 else "포인트 사용"
    return PushMessage(title=title, body=f"{amount:+,}점 · {reason}", url="/")


def queue_after_commit(session: AsyncSession, user_ids: list[int], message: PushMessage) -> None:
    """
    현재 트랜잭션이 커밋된 뒤에 보낼 알림을 쌓아 둡니다. 롤백되면 버려집니다.

    세션이 중첩되면 바깥 `async with session` 블록이 끝날 때 커밋되므로(`DatabaseCore.session`),
    지급 · 차감 함수 안에서 바로 보내지 않고 커밋 이벤트에서 보냅니다.

    Args:
        session: 현재 DB 세션
        user_ids: 알림을 받을 유저 ID
        message: 보낼 메시지
    """
    session.info.setdefault(_PENDING_KEY, []).append((list(user_ids), message))


@event.listens_for(Session, "after_commit")
def _send_queued_after_commit(session: Session) -> None:
    pending: list[tuple[list[int], PushMessage]] | None = session.info.pop(_PENDING_KEY, None)
    if not pending:
        return
    for user_ids, message in pending:
        spawn_background(Notification().send_to_users(user_ids, message))


@event.listens_for(Session, "after_rollback")
def _drop_queued_after_rollback(session: Session) -> None:
    session.info.pop(_PENDING_KEY, None)


@cache
def _vapid() -> Vapid02 | None:
    """설정의 VAPID 개인키로 서명 객체를 만듭니다. 키가 없으면 None"""
    if not (settings.vapid_private_key and settings.vapid_public_key and settings.vapid_subject):
        return None
    return Vapid02.from_string(private_key=settings.vapid_private_key)


def is_enabled() -> bool:
    """VAPID 키가 모두 설정되어 알림을 보낼 수 있는지 반환합니다."""
    return _vapid() is not None


def generate_vapid_keys() -> tuple[str, str]:
    """
    새 VAPID 키 쌍을 만듭니다.

    Returns:
        tuple[str, str]: (공개키, 개인키). 둘 다 base64url 문자열
    """
    from cryptography.hazmat.primitives import serialization

    vapid = Vapid02()
    vapid.generate_keys()
    private_key = b64urlencode(vapid.private_key.private_numbers().private_value.to_bytes(32, "big"))
    public_key = b64urlencode(
        vapid.public_key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    )
    return public_key, private_key


class Notification(BaseCore):
    """
    웹 푸시 구독 관리와 알림 전송 서비스.
    DB 모델 하나를 감싸는 객체가 아니므로 `ServiceCore`가 아닌 `BaseCore`를 상속합니다.
    """

    async def subscribe(self, user_id: int, endpoint: str, p256dh: str, auth: str, user_agent: str | None) -> None:
        """
        기기의 푸시 구독을 등록합니다. 같은 기기(endpoint)를 다른 유저가 쓰고 있었다면 현재 유저로 옮깁니다.

        Args:
            user_id: 구독하는 유저 ID
            endpoint: 푸시 서비스 endpoint
            p256dh: 구독 공개키
            auth: 구독 인증 비밀값
            user_agent: 브라우저 정보
        """
        async with self.session as session:
            result = await session.execute(select(PushSubscriptions).where(col(PushSubscriptions.endpoint) == endpoint))
            subscription = result.scalars().first()
            if subscription is None:
                subscription = PushSubscriptions(user_id=user_id, endpoint=endpoint, p256dh=p256dh, auth=auth)
            subscription.user_id = user_id
            subscription.p256dh = p256dh
            subscription.auth = auth
            subscription.user_agent = user_agent[:300] if user_agent else None
            session.add(subscription)

        self.logs.service_notification.info(f"알림 구독 - 유저 ID {user_id}")

    async def unsubscribe(self, user_id: int, endpoint: str) -> bool:
        """
        현재 유저의 기기 구독을 해제합니다.

        Args:
            user_id: 유저 ID
            endpoint: 해제할 푸시 서비스 endpoint

        Returns:
            bool: 지운 구독이 있으면 True
        """
        async with self.session as session:
            result = await session.execute(
                delete(PushSubscriptions).where(
                    col(PushSubscriptions.endpoint) == endpoint, col(PushSubscriptions.user_id) == user_id
                )
            )
        deleted = (result.rowcount or 0) > 0  # type: ignore[attr-defined]
        if deleted:
            self.logs.service_notification.info(f"알림 구독 해제 - 유저 ID {user_id}")
        return deleted

    async def resolve_targets(self, request: NotificationSend) -> list[int]:
        """
        수동 알림 요청의 대상 유저 ID 목록을 구합니다.

        Args:
            request: 수동 알림 요청

        Returns:
            list[int]: 대상 유저 ID (존재하는 유저만)
        """
        query = select(Users.id)
        match request.target:
            case NotificationTargetType.users:
                query = query.where(col(Users.id).in_(request.user_ids or []))
            case NotificationTargetType.user_type:
                query = query.where(col(Users.type) == request.user_type)
            case NotificationTargetType.class_:
                query = query.where(col(Users.type) == UserType.student, col(Users.grade) == request.grade)
                if request.number is not None:
                    query = query.where(col(Users.number) == request.number)
        async with self.session as session:
            result = await session.execute(query)
        return [int(user_id) for user_id in result.scalars().all()]

    async def count_subscriptions(self, user_ids: list[int]) -> int:
        """
        유저들의 구독(기기) 수를 셉니다.

        Args:
            user_ids: 유저 ID 목록

        Returns:
            int
        """
        if not user_ids:
            return 0
        async with self.session as session:
            result = await session.execute(
                select(func.count()).select_from(PushSubscriptions).where(col(PushSubscriptions.user_id).in_(user_ids))
            )
        return int(result.scalar_one())

    async def send_to_users(self, user_ids: list[int], message: PushMessage) -> int:
        """
        유저들의 모든 구독 기기로 알림을 보냅니다. 만료된 구독(404 · 410)은 지웁니다.
        실패해도 예외를 던지지 않고 로그만 남깁니다. (백그라운드 전송용)

        Args:
            user_ids: 받을 유저 ID 목록
            message: 보낼 메시지

        Returns:
            int: 전송에 성공한 구독 수
        """
        vapid = _vapid()
        if vapid is None:
            self.logs.service_notification.warning("VAPID 키가 설정되지 않아 알림을 보내지 않습니다.")
            return 0
        if not user_ids:
            return 0

        try:
            async with self.session as session:
                result = await session.execute(
                    select(PushSubscriptions).where(col(PushSubscriptions.user_id).in_(user_ids))
                )
                subscriptions = list(result.scalars().all())
            if not subscriptions:
                return 0

            data = message.model_dump_json()
            semaphore = asyncio.Semaphore(PUSH_CONCURRENCY)

            async def send_one(subscription: PushSubscriptions) -> int | None:
                """전송 결과를 상태 코드로 돌려줍니다. 성공은 None"""
                async with semaphore:
                    try:
                        await webpush_async(
                            subscription_info={
                                "endpoint": subscription.endpoint,
                                "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
                            },
                            data=data,
                            vapid_private_key=vapid,
                            # webpush_async가 claims에 aud · exp를 써 넣으므로 구독마다 새 dict를 넘깁니다.
                            vapid_claims={"sub": settings.vapid_subject or ""},
                            ttl=PUSH_TTL_SECONDS,
                            timeout=PUSH_TIMEOUT_SECONDS,
                        )
                        return None
                    except WebPushException as e:
                        return e.status_code or -1
                    except Exception:
                        # 예외 메시지에 endpoint(구독 토큰)가 들어갈 수 있어 종류만 기록합니다.
                        return -1

            statuses = await asyncio.gather(*(send_one(s) for s in subscriptions))

            expired_ids = [
                s.id for s, code in zip(subscriptions, statuses, strict=True) if code in EXPIRED_STATUS_CODES
            ]
            if expired_ids:
                async with self.session as session:
                    await session.execute(delete(PushSubscriptions).where(col(PushSubscriptions.id).in_(expired_ids)))

            sent = statuses.count(None)
            failed = len(statuses) - sent - len(expired_ids)
            self.logs.service_notification.info(
                f"알림 전송 - '{message.title}' 성공 {sent} · 만료 삭제 {len(expired_ids)} · 실패 {failed}"
            )
            return sent
        except Exception as e:
            LoggerCore.service_notification.error(f"알림 전송 실패 - '{message.title}' {type(e).__name__}")
            return 0
