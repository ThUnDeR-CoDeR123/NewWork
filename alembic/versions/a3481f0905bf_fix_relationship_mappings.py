"""Fix relationship mappings

Revision ID: a3481f0905bf
Revises: e56c5b98946d
Create Date: 2025-02-01 19:53:44.173343

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a3481f0905bf'
down_revision: Union[str, None] = 'e56c5b98946d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """
    Fix relationships in tables by adding proper foreign keys and constraints.
    """
    
    
    #Ensure interimwallet has correct ForeignKey mapping
    op.add_column('interimwallet', sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete="CASCADE"), nullable=False))

    

def downgrade() -> None:
    """
    Roll back the relationship fixes by removing the foreign key columns.
    """
    # 🔄 Remove foreign key constraints added in upgrade()
    op.drop_column('interimwallet', 'user_id')

