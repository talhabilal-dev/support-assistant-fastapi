from fastapi import APIRouter, UploadFile, status

from suppport_assistant.core.pagination import Page, PageParamsDep
from suppport_assistant.db.session import SessionDep
from suppport_assistant.modules.auth.dependencies import CurrentUser, SuperUser
from suppport_assistant.modules.knowledge_base.models import SourceType
from suppport_assistant.modules.knowledge_base.pdf import extract_pdf_text
from suppport_assistant.modules.knowledge_base.schemas import (
    DocumentCreate,
    DocumentRead,
    IngestResponse,
    SearchHit,
    SearchRequest,
)
from suppport_assistant.modules.knowledge_base.service import (
    delete_document,
    ingest_document,
    list_documents,
    search,
)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post(
    "/documents", response_model=IngestResponse, status_code=status.HTTP_201_CREATED
)
async def ingest_text(
    payload: DocumentCreate, current_user: SuperUser, session: SessionDep
) -> IngestResponse:
    document, chunks_created = await ingest_document(
        session,
        current_user,
        title=payload.title,
        content=payload.content,
        source=payload.source,
    )
    return IngestResponse(
        document=DocumentRead.model_validate(document),
        chunks_created=chunks_created,
    )


@router.post(
    "/documents/upload",
    response_model=IngestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def ingest_pdf(
    file: UploadFile,
    current_user: SuperUser,
    session: SessionDep,
    title: str | None = None,
) -> IngestResponse:
    data = await file.read()
    text = extract_pdf_text(data)
    document, chunks_created = await ingest_document(
        session,
        current_user,
        title=title or file.filename or "Untitled document",
        content=text,
        source=file.filename,
        source_type=SourceType.PDF,
    )
    return IngestResponse(
        document=DocumentRead.model_validate(document),
        chunks_created=chunks_created,
    )


@router.get("/documents", response_model=Page[DocumentRead])
async def list_all(
    params: PageParamsDep, current_user: CurrentUser, session: SessionDep
) -> Page[DocumentRead]:
    items, total = await list_documents(session, params)
    return Page(
        items=[DocumentRead.model_validate(item) for item in items],
        total=total,
        page=params.page,
        size=params.size,
    )


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    document_id: int, current_user: SuperUser, session: SessionDep
) -> None:
    await delete_document(session, document_id)


@router.post("/search", response_model=list[SearchHit])
async def search_documents(
    payload: SearchRequest, current_user: CurrentUser, session: SessionDep
) -> list[SearchHit]:
    return await search(session, payload.query, payload.top_k)
