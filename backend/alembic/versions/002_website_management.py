"""002_website_management

Revision ID: 002
Revises: 001
Create Date: 2026-08-19 21:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Websites table
    op.create_table(
        'websites',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('organization_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('url', sa.String(length=1024), nullable=False),
        sa.Column('domain', sa.String(length=255), nullable=False),
        sa.Column('public_site_id', sa.String(length=64), nullable=False),
        sa.Column('platform', sa.Enum('WORDPRESS', 'WOOCOMMERCE', 'SHOPIFY', 'CUSTOM', 'UNKNOWN', name='platformenum'), nullable=False),
        sa.Column('status', sa.Enum('ACTIVE', 'INACTIVE', 'PENDING_VERIFICATION', name='websitestatusenum'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_websites_id'), 'websites', ['id'], unique=False)
    op.create_index(op.f('ix_websites_organization_id'), 'websites', ['organization_id'], unique=False)
    op.create_index(op.f('ix_websites_domain'), 'websites', ['domain'], unique=False)
    op.create_index(op.f('ix_websites_public_site_id'), 'websites', ['public_site_id'], unique=True)

    # Website settings table
    op.create_table(
        'website_settings',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('website_id', sa.String(length=36), nullable=False),
        sa.Column('chatbot_name', sa.String(length=255), nullable=False),
        sa.Column('welcome_message', sa.Text(), nullable=False),
        sa.Column('placeholder_text', sa.String(length=255), nullable=False),
        sa.Column('primary_color', sa.String(length=32), nullable=False),
        sa.Column('secondary_color', sa.String(length=32), nullable=False),
        sa.Column('launcher_position', sa.String(length=32), nullable=False),
        sa.Column('widget_size', sa.String(length=32), nullable=False),
        sa.Column('border_radius', sa.String(length=32), nullable=False),
        sa.Column('enable_whatsapp', sa.Boolean(), nullable=False, default=False),
        sa.Column('whatsapp_number', sa.String(length=64), nullable=True),
        sa.Column('custom_instructions', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['website_id'], ['websites.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('website_id')
    )
    op.create_index(op.f('ix_website_settings_id'), 'website_settings', ['id'], unique=False)
    op.create_index(op.f('ix_website_settings_website_id'), 'website_settings', ['website_id'], unique=True)

    # Website domains table
    op.create_table(
        'website_domains',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('website_id', sa.String(length=36), nullable=False),
        sa.Column('domain', sa.String(length=255), nullable=False),
        sa.Column('is_primary', sa.Boolean(), nullable=False, default=False),
        sa.Column('is_verified', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['website_id'], ['websites.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_website_domains_id'), 'website_domains', ['id'], unique=False)
    op.create_index(op.f('ix_website_domains_website_id'), 'website_domains', ['website_id'], unique=False)
    op.create_index(op.f('ix_website_domains_domain'), 'website_domains', ['domain'], unique=False)


def downgrade() -> None:
    op.drop_table('website_domains')
    op.drop_table('website_settings')
    op.drop_table('websites')
    op.execute('DROP TYPE IF EXISTS platformenum')
    op.execute('DROP TYPE IF EXISTS websitestatusenum')
