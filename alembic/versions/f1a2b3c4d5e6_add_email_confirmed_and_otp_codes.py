"""add_email_confirmed_and_otp_codes

Revision ID: f1a2b3c4d5e6
Revises: ea044ed96245
Create Date: 2026-03-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'a87adc826289'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add email_confirmed column to users table
    op.add_column(
        'users',
        sa.Column('email_confirmed', sa.Boolean(), server_default='false', nullable=False),
    )

    # Create otp_codes table
    op.create_table(
        'otp_codes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('code', sa.String(6), nullable=False),
        sa.Column('purpose', sa.String(), nullable=False, server_default='login'),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_otp_codes_id'), 'otp_codes', ['id'], unique=False)
    op.create_index(op.f('ix_otp_codes_user_id'), 'otp_codes', ['user_id'], unique=False)
    op.create_index(op.f('ix_otp_codes_email'), 'otp_codes', ['email'], unique=False)

    # Mark all existing users as email_confirmed (they registered before this feature)
    op.execute("UPDATE users SET email_confirmed = true")


def downgrade() -> None:
    op.drop_index(op.f('ix_otp_codes_email'), table_name='otp_codes')
    op.drop_index(op.f('ix_otp_codes_user_id'), table_name='otp_codes')
    op.drop_index(op.f('ix_otp_codes_id'), table_name='otp_codes')
    op.drop_table('otp_codes')
    op.drop_column('users', 'email_confirmed')
