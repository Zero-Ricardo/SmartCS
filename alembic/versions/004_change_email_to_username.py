"""change_email_to_username

Revision ID: 004
Revises: 21f926fa027e
Create Date: 2026-04-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '21f926fa027e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 删除旧的 email 索引
    op.drop_index('ix_admin_users_email', table_name='admin_users')

    # 将 email 列重命名为 username
    op.alter_column('admin_users', 'email', new_column_name='username')

    # 修改 username 列的长度
    op.alter_column('admin_users', 'username', type_=sa.String(length=100))

    # 创建新的 username 索引
    op.create_index('ix_admin_users_username', 'admin_users', ['username'], unique=True)


def downgrade() -> None:
    # 删除 username 索引
    op.drop_index('ix_admin_users_username', table_name='admin_users')

    # 将 username 列重命名回 email
    op.alter_column('admin_users', 'username', new_column_name='email')

    # 修改 email 列的长度
    op.alter_column('admin_users', 'email', type_=sa.String(length=255))

    # 创建旧的 email 索引
    op.create_index('ix_admin_users_email', 'admin_users', ['email'], unique=True)
