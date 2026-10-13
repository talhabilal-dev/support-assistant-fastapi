from datetime import datetime

from pydantic import Field
from sqlmodel import SQLModel

from suppport_assistant.modules.knowledge_base.models import SourceType


class DocumentCreate(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    source: str | None = Field(default=None, max_length=512)


class DocumentRead(SQLModel):
    id: int
    title: str
    source: str | None
    source_type: SourceType
    created_by_id: int
    created_at: datetime
    updated_at: datetime


class IngestResponse(SQLModel):
    document: DocumentRead
    chunks_created: int


class SearchRequest(SQLModel):
    query: str = Field(min_length=1)
    top_k: int | None = Field(default=None, ge=1, le=50)


class SearchHit(SQLModel):
    chunk_id: int
    document_id: int
    document_title: str
    chunk_index: int
    content: str
    distance: float
