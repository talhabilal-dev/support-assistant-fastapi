from functools import lru_cache

from langchain_openai import OpenAIEmbeddings

from suppport_assistant.core.config import settings


@lru_cache
def _client() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        openai_api_key=settings.openai_api_key or None,
        dimensions=settings.embedding_dimension,
    )


async def embed_texts(texts: list[str]) -> list[list[float]]:
    return await _client().aembed_documents(texts)


async def embed_query(text: str) -> list[float]:
    return await _client().aembed_query(text)
