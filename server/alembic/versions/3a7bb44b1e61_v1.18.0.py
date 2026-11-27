"""v1.18.0 (앱 알림 구독 테이블 추가, 알림 보내기 권한 부여)

Revision ID: 3a7bb44b1e61
Revises: a7d5de15630f
Create Date: 2026-11-27 02:10:00.000000

"""

from collections.abc import Sequence
from enum import IntFlag
from logging import getLogger

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3a7bb44b1e61"
down_revision: str | Sequence[str] | None = "a7d5de15630f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

log = getLogger("alembic.runtime.migration")


# feat/notification (#42)
# 마이그레이션 시점의 권한 비트를 고정하기 위해 app.schemas를 import하지 않고 필요한 값만 복사해 둔다.
class UserPermission(IntFlag):
    NONE = 0

    _MANAGE_USER = 2**13
    SEARCH_USER = 2**17
    _SEND_NOTIFICATION = 2**26
    SEND_NOTIFICATION = _SEND_NOTIFICATION | SEARCH_USER


users = sa.table(
    "users",
    sa.column("id", sa.Integer),
    sa.column("permissions", sa.Integer),
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


def _migrate_notification_permissions(*, grant: bool):
    """
    유저 관리 권한(MANAGE_USER) 보유자(관리자)에게 알림 보내기 권한(SEND_NOTIFICATION)을 부여(grant=True)하거나 제거(grant=False)한다.
    """
    conn = op.get_bind()
    # 회수할 때는 알림 비트만 뺀다. (묶음 값으로 빼면 관리자가 원래 가진 SEARCH_USER까지 빠짐)
    change = {"grant": UserPermission.SEND_NOTIFICATION} if grant else {"revoke": UserPermission._SEND_NOTIFICATION}

    n = _update_permissions(conn, users.c.permissions.op("&")(UserPermission._MANAGE_USER.value) != 0, **change)
    log.info(f"Notification permission migration - admin SEND_NOTIFICATION: {n} rows")


def upgrade() -> None:
    """Upgrade schema."""

    # feat/notification (#42)
    op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("endpoint", sa.String(length=512), nullable=False),
        sa.Column("p256dh", sa.String(length=200), nullable=False),
        sa.Column("auth", sa.String(length=100), nullable=False),
        sa.Column("user_agent", sa.String(length=300), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("endpoint"),
    )
    op.create_index(op.f("ix_push_subscriptions_user_id"), "push_subscriptions", ["user_id"], unique=False)

    log.info("Proceeding with the Users notification permission migration")
    _migrate_notification_permissions(grant=True)
    log.info("Users notification permission migration completed")


def downgrade() -> None:
    """Downgrade schema."""

    # feat/notification (#42)
    log.info("Proceeding with the Users notification permission migration (revoke)")
    _migrate_notification_permissions(grant=False)
    log.info("Users notification permission migration completed")

    # MySQL은 FK 제약이 참조 중인 단일 컬럼 인덱스를 개별 DROP INDEX 하는 것을 허용하지 않으므로(에러 1553)
    # drop_table()로 인덱스/FK를 함께 정리한다.
    op.drop_table("push_subscriptions")
