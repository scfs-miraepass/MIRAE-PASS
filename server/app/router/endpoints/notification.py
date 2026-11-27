from fastapi import APIRouter, HTTPException, Request, status

from app.core import LoginDep, ServiceClient
from app.core.service import Notification
from app.core.service.notification import is_enabled, spawn_background
from app.core.config import settings
from app.schemas import (
    NotificationKey,
    NotificationSend,
    NotificationSendResult,
    PushMessage,
    PushSubscriptionDelete,
    PushSubscriptionOperation,
    UserPermission,
)
from app.schemas.response import ResponseModel, api_responses

router = APIRouter(prefix="/notification", tags=["notification"])
client = ServiceClient()
notification = Notification()


@router.get(
    "/key",
    response_model=ResponseModel[NotificationKey],
    responses=api_responses(
        {
            200: "공개키 조회 성공",
            401: "세션이 만료되었거나 유효하지 않음",
        }
    ),
    status_code=status.HTTP_200_OK,
    summary="알림 공개키 조회",
    description=(
        "기기에서 푸시를 구독할 때 쓰는 VAPID 공개키를 조회합니다. "
        "서버에 VAPID 키가 설정되지 않아 알림을 쓸 수 없으면 `public_key`가 null입니다."
    ),
)
async def get_notification_key(auth_data: LoginDep):
    return ResponseModel(
        success=True, data=NotificationKey(public_key=settings.vapid_public_key if is_enabled() else None)
    )


@router.put(
    "/subscription",
    responses=api_responses(
        {
            204: "구독 등록 성공",
            401: "세션이 만료되었거나 유효하지 않음",
            422: "지원하지 않는 푸시 서비스이거나 요청 형식이 올바르지 않음",
            503: "서버에 알림 설정이 되어 있지 않음",
        }
    ),
    status_code=status.HTTP_204_NO_CONTENT,
    summary="알림 구독 등록",
    description=(
        "이 기기의 푸시 구독을 등록합니다. 본문은 브라우저의 `PushSubscription.toJSON()` 값입니다. "
        "같은 기기를 다른 유저가 구독하고 있었다면 로그인한 유저로 옮깁니다."
    ),
)
async def subscribe_notification(operation: PushSubscriptionOperation, request: Request, auth_data: LoginDep):
    user, _ = auth_data
    if not is_enabled():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="알림 기능이 설정되지 않았어요.")

    await notification.subscribe(
        user_id=user.id,
        endpoint=operation.endpoint,
        p256dh=operation.keys.p256dh,
        auth=operation.keys.auth,
        user_agent=request.headers.get("user-agent"),
    )


@router.delete(
    "/subscription",
    responses=api_responses(
        {
            204: "구독 해제 성공 (구독이 없어도 성공)",
            401: "세션이 만료되었거나 유효하지 않음",
        }
    ),
    status_code=status.HTTP_204_NO_CONTENT,
    summary="알림 구독 해제",
    description="이 기기의 푸시 구독을 해제합니다. 로그아웃하기 전에 호출합니다.",
)
async def unsubscribe_notification(operation: PushSubscriptionDelete, auth_data: LoginDep):
    user, _ = auth_data
    await notification.unsubscribe(user_id=user.id, endpoint=operation.endpoint)


@router.post(
    "/send",
    response_model=ResponseModel[NotificationSendResult],
    responses=api_responses(
        {
            200: "알림 전송 시작",
            401: "세션이 만료되었거나 유효하지 않음",
            403: "권한이 없음",
            404: "대상 유저가 없음",
            422: "대상 조건이 올바르지 않음",
            503: "서버에 알림 설정이 되어 있지 않음",
        }
    ),
    status_code=status.HTTP_200_OK,
    summary="알림 보내기 (관리자)",
    description=(
        "대상(전체 · 유저 선택 · 계정 종류 · 학년/반)을 골라 앱 알림을 보냅니다. "
        "대상과 기기 수를 바로 반환하고, 실제 전송은 백그라운드에서 진행합니다. "
        "알림을 켜지 않은 유저에게는 가지 않습니다."
    ),
)
async def send_notification(request: NotificationSend, auth_data: LoginDep):
    user, _ = auth_data
    if not user.has_permission(UserPermission.SEND_NOTIFICATION):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="권한이 없습니다.")
    if not is_enabled():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="알림 기능이 설정되지 않았어요.")

    user_ids = await notification.resolve_targets(request)
    if not user_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="알림을 받을 유저가 없어요.")
    subscriptions = await notification.count_subscriptions(user_ids)

    message = PushMessage(title=request.title, body=request.body, url=request.url)
    spawn_background(notification.send_to_users(user_ids, message))
    client.logs.service_notification.info(
        f"관리자 알림 보내기 - {user.name}({user.id}) 대상 {request.target.value} {len(user_ids)}명 · 기기 {subscriptions}대"
    )

    return ResponseModel(
        success=True, data=NotificationSendResult(target_users=len(user_ids), subscriptions=subscriptions)
    )
