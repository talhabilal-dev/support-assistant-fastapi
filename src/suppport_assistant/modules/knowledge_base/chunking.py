from langchain_text_splitters import RecursiveCharacterTextSplitter

from suppport_assistant.core.config import settings


def split_text(text: str) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.rag_chunk_size,
        chunk_overlap=settings.rag_chunk_overlap,
    )
    return [chunk for chunk in splitter.split_text(text) if chunk.strip()]
