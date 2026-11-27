"""v1.18.0 (급식 보기 권한 부여)

Revision ID: 0c9493ae7c8c
Revises: a7d5de15630f
Create Date: 2026-11-27 01:12:16.057701

"""

from collections.abc import Sequence
from enum import IntFlag, StrEnum
from logging import getLogger

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0c9493ae7c8c"
down_revision: str | Sequence[str] | None = "a7d5de15630f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

log = getLogger("alembic.runtime.migration")


# feat/meal (#39)
# 마이그레이션 시점의 권한 비트를 고정하기 위해 app.schemas를 import하지 않고 필요한 값만 복사해 둔다.
class UserPermission(IntFlag):
    NONE = 0

    VIEW_MEAL = 2**25


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


def _migrate_meal_permissions(*, grant: bool):
    """
    급식 보기 권한(VIEW_MEAL)을 학생 / 교사에게 부여(grant=True)하거나 제거(grant=False)한다.
    """
    conn = op.get_bind()
    key = "grant" if grant else "revoke"

    n = _update_permissions(
        conn, users.c.type.in_([UserType.student.value, UserType.teacher.value]), **{key: UserPermission.VIEW_MEAL}
    )
    log.info(f"Meal permission migration - student/teacher VIEW_MEAL: {n} rows")


def upgrade() -> None:
    """Upgrade schema."""

    # feat/meal (#39)
    log.info("Proceeding with the Users meal permission migration")
    _migrate_meal_permissions(grant=True)
    log.info("Users meal permission migration completed")


def downgrade() -> None:
    """Downgrade schema."""

    # feat/meal (#39)
    log.info("Proceeding with the Users meal permission migration (revoke)")
    _migrate_meal_permissions(grant=False)
    log.info("Users meal permission migration completed")
