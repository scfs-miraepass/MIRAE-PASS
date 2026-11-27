"""v1.18.0

Revision ID: 6505ebef7b2b
Revises: a7d5de15630f
Create Date: 2026-11-27 10:26:37.909281

"""

from collections.abc import Sequence
from enum import IntFlag, StrEnum
from logging import getLogger

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = "6505ebef7b2b"
down_revision: str | Sequence[str] | None = "a7d5de15630f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

log = getLogger("alembic.runtime.migration")

HISTORY_TYPES_BEFORE = (
    "teacher",
    "cafe",
    "food",
    "etc",
    "grant",
    "quest",
    "stamp",
    "stamp_bonus",
    "karaoke_bid",
    "karaoke_cancel",
)
HISTORY_TYPES_AFTER = (*HISTORY_TYPES_BEFORE, "attendance", "attendance_bonus")


# feat/attendance
# 마이그레이션 시점의 권한 비트를 고정하기 위해 app.schemas를 import하지 않고 필요한 값만 복사해 둔다.
class UserPermission(IntFlag):
    NONE = 0

    CHECK_ATTENDANCE = 2**25


class UserType(StrEnum):
    student = "student"
    teacher = "teacher"
    service = "service"


users = sa.table(
    "users",
    sa.column("id", sa.Integer),
    sa.column("permissions", sa.Integer),
    sa.column("type", sa.String(length=20)),
)


def _update_permissions(conn, where, *, grant: UserPermission | None = None, revoke: UserPermission | None = None):
    rows = conn.execute(sa.select(users.c.id, users.c.permissions).where(where)).all()
    for user_id, permissions in rows:
        perm = UserPermission(permissions)
        if grant is not None:
            perm |= grant
        if revoke is not None:
            perm &= ~revoke
        conn.execute(users.update().where(users.c.id == user_id).values(permissions=perm.value))
    return len(rows)


def _migrate_attendance_permissions(*, grant: bool):
    """
    출석체크 권한 비트를 부여(grant=True)하거나 제거(grant=False)한다.

    - 학생 / 교사: CHECK_ATTENDANCE
    """
    conn = op.get_bind()
    key = "grant" if grant else "revoke"

    n = _update_permissions(
        conn,
        users.c.type.in_([UserType.student.value, UserType.teacher.value]),
        **{key: UserPermission.CHECK_ATTENDANCE},
    )
    log.info(f"Attendance permission migration - student/teacher CHECK_ATTENDANCE: {n} rows")


def upgrade() -> None:
    """Upgrade schema."""

    # feat/attendance
    op.create_table(
        "attendances",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("attend_date", sa.Date(), nullable=False),
        sa.Column("streak", sa.Integer(), nullable=False),
        sa.Column("reward", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "attend_date", name="uq_attendances_user_id_attend_date"),
    )
    op.create_index(op.f("ix_attendances_user_id"), "attendances", ["user_id"], unique=False)

    # PointHistoryType에 출석체크 종류가 추가되어 users.history_type(ENUM) 값 목록도 함께 늘린다.
    op.alter_column(
        "users",
        "history_type",
        existing_type=mysql.ENUM(*HISTORY_TYPES_BEFORE),
        type_=sa.Enum(*HISTORY_TYPES_AFTER, name="pointhistorytype"),
        existing_nullable=True,
    )

    log.info("Proceeding with the Users attendance permission migration")
    _migrate_attendance_permissions(grant=True)
    log.info("Users attendance permission migration completed")


def downgrade() -> None:
    """Downgrade schema."""

    # feat/attendance
    log.info("Proceeding with the Users attendance permission migration (revoke)")
    _migrate_attendance_permissions(grant=False)
    log.info("Users attendance permission migration completed")

    op.alter_column(
        "users",
        "history_type",
        existing_type=sa.Enum(*HISTORY_TYPES_AFTER, name="pointhistorytype"),
        type_=mysql.ENUM(*HISTORY_TYPES_BEFORE),
        existing_nullable=True,
    )

    # MySQL은 FK 제약이 참조 중인 단일 컬럼 인덱스를 개별 DROP INDEX 하는 것을 허용하지 않으므로(에러 1553)
    # drop_table()로 인덱스/FK를 함께 정리한다.
    op.drop_table("attendances")
