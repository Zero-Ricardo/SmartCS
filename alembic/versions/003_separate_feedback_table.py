"""Separate feedback table and remove feedback from messages

Revision ID: 003
Revises: 2c2b9ab5dc03
Create Date: 2026-03-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '003'
down_revision: Union[str, None] = '2c2b9ab5dc03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 创建反馈类型枚举
    op.execute("CREATE TYPE feedbacktype AS ENUM ('up', 'down')")

    # 2. 创建独立反馈表
    op.create_table(
        'chat_feedbacks',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('message_id', sa.String(36), nullable=False),
        sa.Column('session_id', sa.String(36), nullable=False),
        sa.Column('feedback_type', sa.String(10), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['message_id'], ['chat_messages.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 3. 创建索引（便于统计分析）
    op.create_index('ix_chat_feedbacks_message_id', 'chat_feedbacks', ['message_id'])
    op.create_index('ix_chat_feedbacks_session_id', 'chat_feedbacks', ['session_id'])
    op.create_index('ix_chat_feedbacks_type_created', 'chat_feedbacks', ['feedback_type', 'created_at'])

    # 4. 迁移现有反馈数据到新表
    op.execute("""
        INSERT INTO chat_feedbacks (id, message_id, session_id, feedback_type, reason, created_at)
        SELECT
            gen_random_uuid()::text,
            id,
            session_id,
            feedback,
            NULL,
            COALESCE(feedback_at, created_at)
        FROM chat_messages
        WHERE feedback IS NOT NULL
    """)

    # 5. 删除 chat_messages 表中的反馈字段
    op.drop_column('chat_messages', 'feedback_at')
    op.drop_column('chat_messages', 'feedback')


def downgrade() -> None:
    # 1. 恢复 chat_messages 表的反馈字段
    op.add_column('chat_messages', sa.Column('feedback', sa.String(10), nullable=True))
    op.add_column('chat_messages', sa.Column('feedback_at', sa.DateTime(), nullable=True))

    # 2. 迁移数据回去
    op.execute("""
        UPDATE chat_messages m
        SET feedback = f.feedback_type, feedback_at = f.created_at
        FROM chat_feedbacks f
        WHERE m.id = f.message_id
    """)

    # 3. 删除反馈表
    op.drop_index('ix_chat_feedbacks_type_created', table_name='chat_feedbacks')
    op.drop_index('ix_chat_feedbacks_session_id', table_name='chat_feedbacks')
    op.drop_index('ix_chat_feedbacks_message_id', table_name='chat_feedbacks')
    op.drop_table('chat_feedbacks')

    # 4. 删除枚举
    op.execute("DROP TYPE feedbacktype")
