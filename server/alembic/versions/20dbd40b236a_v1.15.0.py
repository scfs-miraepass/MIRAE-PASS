"""v1.15.0

Revision ID: 20dbd40b236a
Revises: da0b850e71f1
Create Date: 2026-11-10 14:02:27.428383

"""

from collections.abc import Sequence
from enum import IntFlag, StrEnum
from logging import getLogger

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = "20dbd40b236a"
down_revision: str | Sequence[str] | None = "da0b850e71f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

log = getLogger("alembic.runtime.migration")


# feat/sticker (PR #17)
# 마이그레이션 시점의 권한 비트를 고정하기 위해 app.schemas를 import하지 않고 필요한 값만 복사해 둔다.
class UserPermission(IntFlag):
    NONE = 0

    _MANAGE_USER = 2**13
    SEARCH_USER = 2**17

    _GIVE_STICKER = 2**21
    GIVE_STICKER = _GIVE_STICKER | SEARCH_USER
    VIEW_STICKER = 2**22
    _MANAGE_STICKER = 2**23
    MANAGE_STICKER = _MANAGE_STICKER | SEARCH_USER
    GIVE_CLASS_STICKER = 2**24


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


def _migrate_sticker_permissions(*, grant: bool):
    """
    스티커 권한 비트를 부여(grant=True)하거나 제거(grant=False)한다.

    - 학생 / 교사: VIEW_STICKER (내 스티커, 랭킹 조회)
    - 교사: GIVE_CLASS_STICKER (받은 스티커를 학급에 전달)
    - 서비스 계정: GIVE_STICKER (스티커 지급)
    - 유저 관리 권한(MANAGE_USER) 보유자: MANAGE_STICKER | VIEW_STICKER (지급/회수/초기화/기록)
    """
    conn = op.get_bind()
    key = "grant" if grant else "revoke"

    n = _update_permissions(
        conn, users.c.type.in_([UserType.student.value, UserType.teacher.value]), **{key: UserPermission.VIEW_STICKER}
    )
    log.info(f"Sticker permission migration - student/teacher VIEW_STICKER: {n} rows")

    n = _update_permissions(conn, users.c.type == UserType.teacher.value, **{key: UserPermission.GIVE_CLASS_STICKER})
    log.info(f"Sticker permission migration - teacher GIVE_CLASS_STICKER: {n} rows")

    n = _update_permissions(conn, users.c.type == UserType.service.value, **{key: UserPermission.GIVE_STICKER})
    log.info(f"Sticker permission migration - service GIVE_STICKER: {n} rows")

    n = _update_permissions(
        conn,
        users.c.permissions.op("&")(UserPermission._MANAGE_USER.value) != 0,
        **{key: UserPermission.MANAGE_STICKER | UserPermission.VIEW_STICKER},
    )
    log.info(f"Sticker permission migration - admin MANAGE_STICKER: {n} rows")


def upgrade() -> None:
    """Upgrade schema."""

    # feat/kiosk-password (PR #11)
    op.add_column("users", sa.Column("kiosk_password", sqlmodel.sql.sqltypes.AutoString(), nullable=True))

    # feat/sticker (PR #17)
    op.create_table(
        "sticker_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("memo", sa.String(length=100), nullable=True),
        sa.Column("class_grade", sa.Integer(), nullable=True),
        sa.Column("class_number", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sticker_history_class", "sticker_history", ["class_grade", "class_number"], unique=False)
    op.create_index(op.f("ix_sticker_history_created_at"), "sticker_history", ["created_at"], unique=False)
    op.create_index(op.f("ix_sticker_history_user_id"), "sticker_history", ["user_id"], unique=False)
    op.create_table(
        "sticker_reset",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("reset_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("reset_by_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["reset_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sticker_reset_reset_at"), "sticker_reset", ["reset_at"], unique=False)

    log.info("Proceeding with the Users sticker permission migration")
    _migrate_sticker_permissions(grant=True)
    log.info("Users sticker permission migration completed")


def downgrade() -> None:
    """Downgrade schema."""

    # feat/sticker (PR #17)
    log.info("Proceeding with the Users sticker permission migration (revoke)")
    _migrate_sticker_permissions(grant=False)
    log.info("Users sticker permission migration completed")

    # MySQL은 FK 제약이 참조 중인 단일 컬럼 인덱스를 개별 DROP INDEX 하는 것을 허용하지 않으므로(에러 1553)
    # drop_table()로 인덱스/FK를 함께 정리한다.
    op.drop_table("sticker_reset")
    op.drop_table("sticker_history")

    # feat/kiosk-password (PR #11)
    op.drop_column("users", "kiosk_password")
