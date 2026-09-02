"""009_quotas_usage_and_subscriptions

Revision ID: 009
Revises: 008
Create Date: 2026-08-20 04:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '009'
down_revision: Union[str, None] = '008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'organization_subscriptions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('organization_id', sa.String(length=36), nullable=False),
        sa.Column('tier', sa.String(length=32), nullable=False, default='FREE'),
        sa.Column('status', sa.String(length=32), nullable=False, default='ACTIVE'),
        sa.Column('current_period_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancel_at_period_end', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id')
    )
    op.create_index(op.f('ix_organization_subscriptions_id'), 'organization_subscriptions', ['id'], unique=False)
    op.create_index(op.f('ix_organization_subscriptions_organization_id'), 'organization_subscriptions', ['organization_id'], unique=True)

    op.create_table(
        'organization_usage',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('organization_id', sa.String(length=36), nullable=False),
        sa.Column('billing_period', sa.String(length=7), nullable=False),
        sa.Column('chat_messages_count', sa.Integer(), nullable=False, default=0),
        sa.Column('crawl_pages_count', sa.Integer(), nullable=False, default=0),
        sa.Column('vector_chunks_count', sa.Integer(), nullable=False, default=0),
        sa.Column('tokens_consumed', sa.Integer(), nullable=False, default=0),
        sa.Column('last_reset_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'billing_period', name='uq_org_billing_period')
    )
    op.create_index(op.f('ix_organization_usage_id'), 'organization_usage', ['id'], unique=False)
    op.create_index(op.f('ix_organization_usage_organization_id'), 'organization_usage', ['organization_id'], unique=False)
    op.create_index(op.f('ix_organization_usage_billing_period'), 'organization_usage', ['billing_period'], unique=False)


def downgrade() -> None:
    op.drop_table('organization_usage')
    op.drop_table('organization_subscriptions')
