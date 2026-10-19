"""schedule exception: move to another date and teacher replacement

Revision ID: 9c1f0d7ab254
Revises: feb48b3a624b
Create Date: 2026-10-19 10:00:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = '9c1f0d7ab254'
down_revision: str | None = 'feb48b3a624b'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('schedule_exceptions', sa.Column('new_date', sa.Date(), nullable=True))
    op.add_column('schedule_exceptions', sa.Column('new_teacher_id', sa.Integer(), nullable=True))
    op.create_index(
        op.f('ix_schedule_exceptions_new_date'), 'schedule_exceptions', ['new_date'], unique=False
    )
    op.create_foreign_key(
        'fk_schedule_exceptions_new_teacher_id',
        'schedule_exceptions',
        'teachers',
        ['new_teacher_id'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint(
        'fk_schedule_exceptions_new_teacher_id', 'schedule_exceptions', type_='foreignkey'
    )
    op.drop_index(op.f('ix_schedule_exceptions_new_date'), table_name='schedule_exceptions')
    op.drop_column('schedule_exceptions', 'new_teacher_id')
    op.drop_column('schedule_exceptions', 'new_date')
