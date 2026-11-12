"""v1.15.0

Revision ID: 20dbd40b236a
Revises: da0b850e71f1
Create Date: 2026-11-10 14:02:27.428383

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = "20dbd40b236a"
down_revision: str | Sequence[str] | None = "da0b850e71f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""

    # feat/kiosk-password (PR #11)
    op.add_column("users", sa.Column("kiosk_password", sqlmodel.sql.sqltypes.AutoString(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""

    # feat/kiosk-password (PR #11)
    op.drop_column("users", "kiosk_password")
