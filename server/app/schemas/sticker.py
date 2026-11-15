from datetime import datetime
from typing import Any

from pydantic import field_serializer
from sqlalchemy import Column, DateTime, Index, String, func
from sqlmodel import Field, SQLModel

from .core import SchemaCore


class StickerHistory(SQLModel, table=True):
    """
    스티커 변동 기록 (지급: 양수, 회수: 음수)

    보유 수는 현재 집계 기간(매월 1일 00:00 KST 또는 최근 수동 초기화 시각 이후) 내 `amount` 합계로 계산한다.
    기록은 초기화와 무관하게 영구 보관한다.
    """

    __tablename__ = "sticker_history"  # type: ignore[assignment]
    __table_args__ = (Index("ix_sticker_history_class", "class_grade", "class_number"),)

    id: int | None = Field(default=None, primary_key=True, description="고유 ID")
    user_id: int = Field(
        foreign_key="users.id",
        ondelete="CASCADE",
        index=True,
        description="스티커를 받은 학생의 고유 ID",
    )
    amount: int = Field(description="변동 수량 (지급 +1~+3, 회수 음수)")
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
