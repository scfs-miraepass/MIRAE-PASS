from datetime import date, datetime
from typing import Any

from pydantic import field_serializer
from sqlalchemy import Column, DateTime, UniqueConstraint, func
from sqlmodel import Field, SQLModel

from .core import SchemaCore


class Attendances(SQLModel, table=True):
    """출석체크 기록. 한 유저는 하루(KST)에 한 번만 출석할 수 있습니다."""

    # 같은 날 동시에 들어온 요청도 한 번만 기록되도록 DB에서 한 번 더 막습니다.
    __table_args__ = (UniqueConstraint("user_id", "attend_date", name="uq_attendances_user_id_attend_date"),)

    id: int | None = Field(default=None, primary_key=True, description="고유 ID")
    user_id: int = Field(
        foreign_key="users.id",
        ondelete="CASCADE",
        index=True,
        description="출석한 유저의 고유 ID",
    )
    attend_date: date = Field(description="출석일 (KST 기준 날짜)")
    streak: int = Field(description="이날까지의 연속 출석 일수")
    reward: int = Field(description="지급한 포인트")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(SchemaCore.timezone),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
        description="출석 일시",
    )

    @field_serializer("created_at")
    def serialize_created_at(self, dt: Any, _info):
        if isinstance(dt, datetime):
            return SchemaCore.sync_timezone(dt).isoformat()
        return dt


class AttendanceStatus(SQLModel):
    """오늘의 출석체크 상태"""

    today: date = Field(description="오늘 날짜 (KST)")
    available: bool = Field(description="오늘 출석할 수 있는 날인지 (주말 · 휴업일 · 공휴일이면 false)")
    attended: bool = Field(description="오늘 이미 출석했는지")
    streak: int = Field(description="현재 연속 출석 일수 (끊겼으면 0)")
    days_to_bonus: int = Field(description="다음 보너스까지 남은 출석 일수 (오늘 출석하면 받는 경우 1)")
    reward: int = Field(description="다음 출석 때 받을 포인트")


class AttendanceResult(SQLModel):
    """출석체크 결과"""

    attend_date: date = Field(description="출석일 (KST)")
    streak: int = Field(description="연속 출석 일수")
    reward: int = Field(description="지급한 포인트")
    bonus: bool = Field(description="연속 출석 보너스인지")
    point: int = Field(description="지급 후 보유 포인트")
