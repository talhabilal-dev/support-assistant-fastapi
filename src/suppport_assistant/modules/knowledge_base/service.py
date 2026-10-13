from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from suppport_assistant.core.config import settings
from suppport_assistant.core.errors import AppError, NotFoundError
from suppport_assistant.core.pagination import PageParams
from suppport_assistant.modules.knowledge_base.chunking import split_text
from suppport_assistant.modules.knowledge_base.embeddings import (
    embed_query,
    embed_texts,
)
from suppport_assistant.modules.knowledge_base.models import (
    Chunk,
    Document,
    SourceType,
)
from suppport_assistant.modules.knowledge_base.schemas import SearchHit
from suppport_assistant.modules.users.models import User


async def ingest_document(
    session: AsyncSession,
    user: User,
    *,
    title: str,
    content: str,
    source: str | None = None,
    source_type: SourceType = SourceType.TEXT,
) -> tuple[Document, int]:
    chunks = split_text(content)
    if not chunks:
        raise AppError("Document contains no extractable text")

    embeddings = await embed_texts(chunks)

    document = Document(
        title=title,
        source=source,
        source_type=source_type,
        created_by_id=user.id,
    )
    session.add(document)
    await session.flush()

    session.add_all(
        [
            Chunk(
                document_id=document.id,
                chunk_index=index,
                content=chunk,
                embedding=embedding,
            )
            for index, (chunk, embedding) in enumerate(
                zip(chunks, embeddings, strict=True)
            )
        ]
    )
    await session.commit()
    await session.refresh(document)
    return document, len(chunks)


async def list_documents(
    session: AsyncSession, params: PageParams
) -> tuple[list[Document], int]:
    statement = select(Document).order_by(Document.created_at.desc())
    count_statement = select(func.count()).select_from(Document)

    total = (await session.exec(count_statement)).one()
    statement = statement.offset(params.offset).limit(params.size)
    items = list((await session.exec(statement)).all())
    return items, total


async def get_document(session: AsyncSession, document_id: int) -> Document:
    document = await session.get(Document, document_id)
    if document is None:
        raise NotFoundError("Document not found")
    return document


async def delete_document(session: AsyncSession, document_id: int) -> None:
    document = await get_document(session, document_id)
    await session.delete(document)
    await session.commit()


async def search(
    session: AsyncSession, query: str, top_k: int | None = None
) -> list[SearchHit]:
    query_embedding = await embed_query(query)
    distance = Chunk.embedding.cosine_distance(query_embedding)

    statement = (
        select(Chunk, Document.title, distance.label("distance"))
        .join(Document, Document.id == Chunk.document_id)
        .order_by(distance)
        .limit(top_k or settings.rag_top_k)
    )
    rows = (await session.exec(statement)).all()

    return [
        SearchHit(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            document_title=title,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            distance=float(row_distance),
        )
        for chunk, title, row_distance in rows
    ]
