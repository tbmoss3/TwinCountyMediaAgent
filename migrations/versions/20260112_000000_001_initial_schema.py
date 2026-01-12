"""Initial schema migration.

Revision ID: 001
Revises: None
Create Date: 2026-01-12

This migration represents the baseline schema.
The schema was already created by the application's schema.py,
so this serves as a marker for Alembic to track future changes.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade database schema.

    Note: The initial schema is created by database/schema.py.
    This migration serves as the baseline for future migrations.
    Running this on an existing database will do nothing harmful
    due to IF NOT EXISTS clauses.
    """
    # Create extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # Create alembic_version table if not exists (handled by Alembic)
    # All other tables are created by schema.py with IF NOT EXISTS


def downgrade() -> None:
    """
    Downgrade database schema.

    WARNING: This will drop all tables. Use with extreme caution.
    """
    op.execute('DROP TABLE IF EXISTS newsletter_content_links CASCADE')
    op.execute('DROP TABLE IF EXISTS sent_newsletters CASCADE')
    op.execute('DROP TABLE IF EXISTS scrape_runs CASCADE')
    op.execute('DROP TABLE IF EXISTS source_configs CASCADE')
    op.execute('DROP TABLE IF EXISTS scraped_content CASCADE')
    op.execute('DROP TABLE IF EXISTS system_state CASCADE')
