"""007_commerce_integrations

Revision ID: 007
Revises: 006
Create Date: 2026-08-19 23:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '007'
down_revision: Union[str, None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'commerce_integrations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('website_id', sa.String(length=36), nullable=False),
        sa.Column('organization_id', sa.String(length=36), nullable=False),
        sa.Column('platform', sa.String(length=32), nullable=False, default='WOOCOMMERCE'),
        sa.Column('api_url', sa.String(length=512), nullable=False),
        sa.Column('consumer_key', sa.String(length=255), nullable=False),
        sa.Column('consumer_secret', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['website_id'], ['websites.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('website_id')
    )
    op.create_index(op.f('ix_commerce_integrations_id'), 'commerce_integrations', ['id'], unique=False)
    op.create_index(op.f('ix_commerce_integrations_organization_id'), 'commerce_integrations', ['organization_id'], unique=False)
    op.create_index(op.f('ix_commerce_integrations_website_id'), 'commerce_integrations', ['website_id'], unique=True)


def downgrade() -> None:
    op.drop_table('commerce_integrations')
