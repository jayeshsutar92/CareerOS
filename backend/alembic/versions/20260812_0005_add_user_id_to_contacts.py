"""feat: Add user_id to contacts to secure ownership

Revision ID: 5f1b93c65409
Revises: 9f72ff9f9480
Create Date: 2026-08-12 11:51:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '5f1b93c65409'
down_revision: str | None = '9f72ff9f9480'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add user_id column
    op.add_column('contacts', sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f('ix_contacts_user_id'), 'contacts', ['user_id'], unique=False)
    op.create_foreign_key(
        'fk_contacts_user_id', 
        'contacts', 
        'users', 
        ['user_id'], 
        ['id'], 
        ondelete='CASCADE'
    )

    # Drop old dedupe_key unique constraint
    op.drop_constraint('uq_contacts_dedupe_key', 'contacts', type_='unique')
    
    # Create new compound unique constraint
    op.create_unique_constraint('uq_contacts_user_dedupe_key', 'contacts', ['user_id', 'dedupe_key'])


def downgrade() -> None:
    # Drop new constraint and restore old one
    op.drop_constraint('uq_contacts_user_dedupe_key', 'contacts', type_='unique')
    op.create_unique_constraint('uq_contacts_dedupe_key', 'contacts', ['dedupe_key'])

    # Drop foreign key and column
    op.drop_constraint('fk_contacts_user_id', 'contacts', type_='foreignkey')
    op.drop_index(op.f('ix_contacts_user_id'), table_name='contacts')
    op.drop_column('contacts', 'user_id')
