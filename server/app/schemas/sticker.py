from datetime import datetime
from typing import Any

from pydantic import ConfigDict, field_serializer
from sqlalchemy import Column, DateTime, Index, String, func
from sqlmodel import Field, SQLModel

from .core import SchemaCore
from .users import UserSummary


class StickerHistoryBase(SQLModel):
    """`StickerHistory` 테이블과 응답 모델이 함께 쓰는 필드"""

    id: int | None = Field(default=None, primary_key=True, description="고유 ID")
    user_id: int = Field(
        foreign_key="users.id",
        ondelete="CASCADE",
        index=True,
        description="스티커를 받은 학생의 고유 ID",
    )
    amount: int = Field(description="변동 수량 (지급 양수, 회수 · 학급 전달 음수)")
    actor_id: int | None = Field(
        default=None,
        foreign_key="users.id",
        ondelete="SET NULL",
        description="지급/회수를 처리한 유저의 고유 ID",
    )
    memo: str | None = Field(default=None, sa_column=Column(String(100)), description="메모")
    class_grade: int | None = Field(default=None, description="교사가 학급에 전달한 경우 대상 학년")
    class_number: int | None = Field(default=None, description="교사가 학급에 전달한 경우 대상 반")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(SchemaCore.timezone),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), index=True),
        description="처리 일시",
    )

    @field_serializer("created_at")
    def serialize_created_at(self, dt: Any, _info):
        if isinstance(dt, datetime):
            return SchemaCore.sync_timezone(dt).isoformat()
        return dt


class StickerHistory(StickerHistoryBase, table=True):
    """
    스티커 변동 기록 (지급: 양수, 회수: 음수)

    보유 수는 현재 집계 기간(매월 1일 00:00 KST 또는 최근 수동 초기화 시각 이후) 내 `amount` 합계로 계산한다.
    지급 한도는 이번 주(월요일 00:00 KST 이후, 학급 전달 기록 제외)에 받은 수 기준이다.
    기록은 초기화와 무관하게 영구 보관한다.
    """

    __tablename__ = "sticker_history"  # type: ignore[assignment]
    __table_args__ = (Index("ix_sticker_history_class", "class_grade", "class_number"),)


class StickerHistoryItem(StickerHistoryBase):
    """스티커 기록 조회 응답. 대상 · 처리 유저 정보를 함께 담는다."""

    model_config = ConfigDict(json_schema_serialization_defaults_required=True)

    id: int = Field(..., description="고유 ID")  # type: ignore[assignment]
    user: UserSummary | None = Field(None, description="대상 유저")
    actor: UserSummary | None = Field(None, description="처리한 유저 (삭제된 유저면 null)")


class StickerReset(SQLModel, table=True):
    """관리자가 수동으로 스티커를 초기화한 기록. 가장 최근 `reset_at`이 집계 기간 시작으로 사용될 수 있다."""

    __tablename__ = "sticker_reset"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True, description="고유 ID")
    reset_at: datetime = Field(
        default_factory=lambda: datetime.now(SchemaCore.timezone),
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), index=True),
        description="초기화 일시",
    )
    reset_by_id: int | None = Field(
        default=None,
        foreign_key="users.id",
        ondelete="SET NULL",
        description="초기화를 실행한 유저의 고유 ID",
    )

    @field_serializer("reset_at")
    def serialize_reset_at(self, dt: Any, _info):
        if isinstance(dt, datetime):
            return SchemaCore.sync_timezone(dt).isoformat()
        return dt
