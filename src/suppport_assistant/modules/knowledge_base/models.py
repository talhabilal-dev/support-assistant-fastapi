from datetime import UTC, datetime
from enum import Enum, StrEnum

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel

from suppport_assistant.core.config import settings


class SourceType(StrEnum):
    TEXT = "text"
    PDF = "pdf"


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _enum_column(enum_cls: type[Enum], name: str) -> Column:
    return Column(
        SAEnum(enum_cls, name=name, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )


class Document(SQLModel, table=True):
    __tablename__ = "documents"

    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(max_length=255)
    source: str | None = Field(default=None, max_length=512)
    source_type: SourceType = Field(
        default=SourceType.TEXT,
        sa_column=_enum_column(SourceType, "sourcetype"),
    )
    created_by_id: int = Field(foreign_key="users.id", index=True)
    created_at: datetime = Field(
        default_factory=_utcnow, sa_type=DateTime(timezone=True)
    )
    updated_at: datetime = Field(
        default_factory=_utcnow, sa_type=DateTime(timezone=True)
    )


class Chunk(SQLModel, table=True):
    __tablename__ = "chunks"
    __table_args__ = (
        Index(
            "ix_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    document_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    chunk_index: int
    content: str
    embedding: list[float] = Field(
        sa_column=Column(Vector(settings.embedding_dimension), nullable=False)
    )
    created_at: datetime = Field(
        default_factory=_utcnow, sa_type=DateTime(timezone=True)
    )
