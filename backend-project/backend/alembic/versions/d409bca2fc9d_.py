"""empty message

Revision ID: d409bca2fc9d
Revises: 
Create Date: 2024-08-25 17:43:09.732138

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'd409bca2fc9d'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('stories', sa.Column('textfile_path', sa.String(length=255), nullable=True))
    op.create_index(op.f('ix_stories_textfile_path'), 'stories', ['textfile_path'], unique=False)
    op.drop_column('stories', 'content')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('stories', sa.Column('content', mysql.MEDIUMTEXT(collation='utf8mb3_unicode_ci'), nullable=True))
    op.drop_index(op.f('ix_stories_textfile_path'), table_name='stories')
    op.drop_column('stories', 'textfile_path')
    # ### end Alembic commands ###
