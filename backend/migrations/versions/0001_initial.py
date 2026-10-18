"""Начальная схема: товары и журнал обработанных апдейтов.

Revision ID: 0001_initial
Revises:
Create Date: 2024-10-15
"""

from __future__ import annotations

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE products (
            id uuid PRIMARY KEY,
            title varchar(200) NOT NULL,
            image_key text NOT NULL,
            content_type varchar(64) NOT NULL,
            size_bytes integer NOT NULL,
            created_at timestamptz NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_products_created_at_id
            ON products (created_at DESC, id DESC)
        """
    )
    op.execute(
        """
        CREATE TABLE telegram_updates (
            update_id bigint PRIMARY KEY,
            status varchar(16) NOT NULL,
            received_at timestamptz NOT NULL DEFAULT now(),
            processed_at timestamptz
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE telegram_updates")
    op.execute("DROP INDEX ix_products_created_at_id")
    op.execute("DROP TABLE products")
