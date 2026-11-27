from datetime import datetime
from enum import StrEnum
from typing import Self
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import Column, DateTime, String, func
from sqlmodel import Field as SQLField
from sqlmodel import SQLModel

from .core import SchemaCore
from .users import UserType

PUSH_SERVICE_HOSTS = (
    "fcm.googleapis.com",
    "updates.push.services.mozilla.com",
    "push.services.mozilla.com",
    "web.push.apple.com",
    "notify.windows.com",
)
"""
구독 endpoint로 허용하는 푸시 서비스 호스트 (Chrome · Firefox · Safari · Edge).
서버가 사용자가 보낸 임의의 주소로 요청을 보내지 않도록(SSRF 방지) 이 호스트와 그 하위 도메인만 허용합니다.
"""


class PushSubscriptions(SQLModel, table=True):
    """기기(브라우저)별 웹 푸시 구독 정보. 한 유저가 여러 기기를 구독할 수 있다."""

    __tablename__ = "push_subscriptions"  # type: ignore[assignment]

    id: int | None = SQLField(default=None, primary_key=True, description="고유 ID")
    user_id: int = SQLField(foreign_key="users.id", ondelete="CASCADE", index=True, description="구독한 유저의 고유 ID")
    endpoint: str = SQLField(
        sa_column=Column(String(512), nullable=False, unique=True), description="푸시 서비스 endpoint URL"
    )
    p256dh: str = SQLField(sa_column=Column(String(200), nullable=False), description="구독 공개키 (base64url)")
    auth: str = SQLField(sa_column=Column(String(100), nullable=False), description="구독 인증 비밀값 (base64url)")
    user_agent: str | None = SQLField(default=None, sa_column=Column(String(300)), description="구독한 브라우저 정보")
    created_at: datetime = SQLField(
        default_factory=lambda: datetime.now(SchemaCore.timezone),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
        description="구독 일시",
    )


class PushSubscriptionKeys(BaseModel):
    p256dh: str = Field(
        ..., min_length=1, max_length=200, description="구독 공개키 (PushSubscription.toJSON().keys.p256dh)"
    )
    auth: str = Field(
        ..., min_length=1, max_length=100, description="구독 인증 비밀값 (PushSubscription.toJSON().keys.auth)"
    )


class PushSubscriptionOperation(BaseModel):
    endpoint: str = Field(..., max_length=512, description="푸시 서비스 endpoint (PushSubscription.endpoint)")
    keys: PushSubscriptionKeys = Field(..., description="구독 키")

    @field_validator("endpoint")
    @classmethod
    def validate_endpoint(cls, value: str) -> str:
        url = urlparse(value)
        host = url.hostname or ""
        if url.scheme != "https" or not any(host == h or host.endswith(f".{h}") for h in PUSH_SERVICE_HOSTS):
            raise ValueError("지원하지 않는 푸시 서비스입니다.")
        return value


class PushSubscriptionDelete(BaseModel):
    endpoint: str = Field(..., max_length=512, description="해제할 푸시 서비스 endpoint (PushSubscription.endpoint)")


class NotificationKey(BaseModel):
    public_key: str | None = Field(
        None, description="VAPID 공개키 (base64url). 서버에 VAPID 키가 설정되지 않아 알림을 쓸 수 없으면 null"
    )


class PushMessage(BaseModel):
    """서비스 워커로 보내는 푸시 메시지 (JSON)"""

    title: str = Field(..., description="알림 제목")
    body: str = Field(..., description="알림 내용")
    url: str = Field("/", description="알림을 눌렀을 때 열 앱 안 경로")


class NotificationTargetType(StrEnum):
    """수동 알림 대상 종류"""

    all = "all"
    users = "users"
    user_type = "user_type"
    class_ = "class"


class NotificationSend(BaseModel):
    title: str = Field(..., min_length=1, max_length=50, description="알림 제목")
    body: str = Field(..., min_length=1, max_length=200, description="알림 내용")
    url: str = Field("/", max_length=200, description="알림을 눌렀을 때 열 앱 안 경로 (/로 시작)")
    target: NotificationTargetType = Field(
        ...,
        description="대상 종류 (all: 전체, users: 유저 선택, user_type: 계정 종류, class: 학년 · 반)",
    )
    user_ids: list[int] | None = Field(
        None, min_length=1, max_length=1000, description="target=users일 때 대상 유저 ID"
    )
    user_type: UserType | None = Field(None, description="target=user_type일 때 계정 종류")
    grade: int | None = Field(None, ge=1, le=9, description="target=class일 때 학년")
    number: int | None = Field(None, ge=1, le=99, description="target=class일 때 반. 생략하면 학년 전체")

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        # 앱 밖 주소(//example.com, https://...)로 열리지 않도록 앱 안 경로만 허용합니다.
        if not value.startswith("/") or value.startswith("//") or "\\" in value:
            raise ValueError("url은 /로 시작하는 앱 안 경로여야 합니다.")
        return value

    @model_validator(mode="after")
    def validate_target(self) -> Self:
        if self.target == NotificationTargetType.users and not self.user_ids:
            raise ValueError("유저 선택일 때는 user_ids가 필요합니다.")
        if self.target == NotificationTargetType.user_type and self.user_type is None:
            raise ValueError("계정 종류 선택일 때는 user_type이 필요합니다.")
        if self.target == NotificationTargetType.class_ and self.grade is None:
            raise ValueError("학년 · 반 선택일 때는 grade가 필요합니다.")
        return self


class NotificationSendResult(BaseModel):
    target_users: int = Field(..., description="대상 유저 수")
    subscriptions: int = Field(..., description="알림을 보낼 기기(구독) 수. 알림을 켜지 않은 유저는 포함되지 않음")
