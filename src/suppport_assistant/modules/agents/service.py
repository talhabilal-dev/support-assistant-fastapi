from functools import lru_cache
from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import BaseMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from sqlmodel.ext.asyncio.session import AsyncSession

from suppport_assistant.core.config import settings
from suppport_assistant.modules.knowledge_base.service import search as search_hits
from suppport_assistant.modules.tickets.models import TicketPriority
from suppport_assistant.modules.tickets.schemas import TicketCreate
from suppport_assistant.modules.tickets.service import create_ticket
from suppport_assistant.modules.users.models import User

SYSTEM_PROMPT = (
    "You are the Suppport Assistant, a customer-support agent. "
    "Answer ONLY with facts stated in the knowledge-base passages returned by the "
    "search_knowledge_base tool, and always call that tool before answering. "
    "Hard rules: "
    "(1) Never state a policy, rule, number, date, price, or entity that is not "
    "written in the retrieved passages. "
    "(2) Never say or imply what the policy does NOT allow or cover, and never draw "
    "conclusions beyond the passages (no 'therefore', no 'you cannot', no 'after N "
    "days'). "
    "(3) If the passages do not answer the question, reply that you could not find "
    "that information in the documents. Do not guess. "
    "(4) If only part of the question is covered, answer that part and say the rest "
    "is not covered by the documents. "
    "(5) Cite the chunk ids you used inline, for example (source: chunk 12). "
    "If the user asks to escalate or report a problem, call create_support_ticket and "
    "tell them the ticket number."
)


@lru_cache
def get_chat_model() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.openai_api_key or None,
        temperature=settings.llm_temperature,
    )


def build_tools(
    session: AsyncSession,
    user: User,
    sources: list[str],
    contexts: list[dict[str, str]],
) -> list[Any]:
    @tool
    async def search_knowledge_base(query: str) -> str:
        """Search the internal knowledge base and return the most relevant passages."""
        hits = await search_hits(session, query)
        hits = [hit for hit in hits if hit.distance <= settings.rag_max_distance]
        if not hits:
            return "No relevant knowledge base entries were found."
        for hit in hits:
            citation = f"{hit.document_title} (chunk {hit.chunk_id})"
            if citation not in sources:
                sources.append(citation)
            contexts.append(
                {
                    "chunk_id": str(hit.chunk_id),
                    "document_title": hit.document_title,
                    "content": hit.content,
                }
            )
        return "\n\n".join(
            f"[chunk {hit.chunk_id}] {hit.document_title}: {hit.content}"
            for hit in hits
        )

    @tool
    async def create_support_ticket(
        subject: str, description: str, priority: str = "medium"
    ) -> str:
        """Open a support ticket to escalate or report an issue."""
        try:
            ticket_priority = TicketPriority(priority.lower())
        except ValueError:
            ticket_priority = TicketPriority.MEDIUM

        ticket = await create_ticket(
            session,
            user,
            TicketCreate(
                subject=subject,
                description=description,
                priority=ticket_priority,
            ),
        )
        return f"Created support ticket #{ticket.id}: '{ticket.subject}'."

    return [search_knowledge_base, create_support_ticket]


def build_agent(
    session: AsyncSession,
    user: User,
    sources: list[str],
    contexts: list[dict[str, str]],
) -> Any:
    return create_agent(
        get_chat_model(),
        build_tools(session, user, sources, contexts),
        system_prompt=SYSTEM_PROMPT,
    )


def _message_text(message: BaseMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "\n".join(part for part in parts if part)
    return str(content)


async def generate_reply(
    session: AsyncSession, user: User, messages: list[dict[str, str]]
) -> tuple[str, list[str], list[dict[str, str]]]:
    sources: list[str] = []
    contexts: list[dict[str, str]] = []
    agent = build_agent(session, user, sources, contexts)
    result = await agent.ainvoke({"messages": messages})
    return _message_text(result["messages"][-1]), sources, contexts
