"""006_conversation_inbox_and_agent_takeover

Revision ID: 006
Revises: 005
Create Date: 2026-08-19 23:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('chat_sessions', sa.Column('status', sa.String(length=32), nullable=False, server_default='BOT_ACTIVE'))
    op.add_column('chat_sessions', sa.Column('assigned_user_id', sa.String(length=36), nullable=True))
    op.add_column('chat_sessions', sa.Column('last_message_at', sa.DateTime(timezone=True), nullable=True))

    op.create_index(op.f('ix_chat_sessions_status'), 'chat_sessions', ['status'], unique=False)
    op.create_index(op.f('ix_chat_sessions_assigned_user_id'), 'chat_sessions', ['assigned_user_id'], unique=False)
    op.create_index(op.f('ix_chat_sessions_last_message_at'), 'chat_sessions', ['last_message_at'], unique=False)
    op.create_foreign_key('fk_chat_sessions_assigned_user', 'chat_sessions', 'users', ['assigned_user_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    op.drop_constraint('fk_chat_sessions_assigned_user', 'chat_sessions', type_='foreignkey')
    op.drop_index(op.f('ix_chat_sessions_last_message_at'), table_name='chat_sessions')
    op.drop_index(op.f('ix_chat_sessions_assigned_user_id'), table_name='chat_sessions')
    op.drop_index(op.f('ix_chat_sessions_status'), table_name='chat_sessions')
    op.drop_column('chat_sessions', 'last_message_at')
    op.drop_column('chat_sessions', 'assigned_user_id')
    op.drop_column('chat_sessions', 'status')
