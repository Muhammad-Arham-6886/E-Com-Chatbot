"""008_whatsapp_handoff_customization

Revision ID: 008
Revises: 007
Create Date: 2026-08-20 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '008'
down_revision: Union[str, None] = '007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('website_settings', sa.Column('whatsapp_custom_message', sa.Text(), nullable=True))
    op.add_column('website_settings', sa.Column('whatsapp_handoff_trigger', sa.String(length=32), nullable=False, server_default='ON_ESCALATION'))


def downgrade() -> None:
    op.drop_column('website_settings', 'whatsapp_handoff_trigger')
    op.drop_column('website_settings', 'whatsapp_custom_message')
