"""Add persistent report chunk embeddings."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy


revision: str = "65e7a1d7095c"
down_revision: Union[str, Sequence[str], None] = "3e7ad7658788"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "report_chunks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("document", sa.String(500), nullable=False),
        sa.Column("page", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("model_name", sa.String(255), nullable=False),
        sa.Column(
            "embedding",
            pgvector.sqlalchemy.Vector(dim=384),
            nullable=False,
        ),
    )

    op.create_index(
        "uq_report_chunks_identity",
        "report_chunks",
        ["document", "page", "chunk_index"],
        unique=True,
    )
    op.create_index(
        "ix_report_chunks_content_hash",
        "report_chunks",
        ["content_hash"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_report_chunks_content_hash",
        table_name="report_chunks",
    )
    op.drop_index(
        "uq_report_chunks_identity",
        table_name="report_chunks",
    )
    op.drop_table("report_chunks")