from datetime import UTC, datetime

from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from suppport_assistant.core.errors import NotFoundError, PermissionDeniedError
from suppport_assistant.core.pagination import PageParams
from suppport_assistant.modules.agents.service import generate_reply
from suppport_assistant.modules.conversations.models import (
    Conversation,
    Message,
    MessageRole,
)
from suppport_assistant.modules.conversations.schemas import (
    ConversationCreate,
    MessageCreate,
)
from suppport_assistant.modules.users.models import User

DEFAULT_TITLE = "New conversation"


def _authorize(user: User, conversation: Conversation) -> None:
    if user.is_superuser or conversation.user_id == user.id:
        return
    raise PermissionDeniedError()


async def create_conversation(
    session: AsyncSession, user: User, data: ConversationCreate
) -> Conversation:
    conversation = Conversation(user_id=user.id, title=data.title or DEFAULT_TITLE)
    session.add(conversation)
    await session.commit()
    await session.refresh(conversation)
    return conversation


async def list_conversations(
    session: AsyncSession, user: User, params: PageParams
) -> tuple[list[Conversation], int]:
    statement = select(Conversation).order_by(Conversation.updated_at.desc())
    count_statement = select(func.count()).select_from(Conversation)

    if not user.is_superuser:
        statement = statement.where(Conversation.user_id == user.id)
        count_statement = count_statement.where(Conversation.user_id == user.id)

    total = (await session.exec(count_statement)).one()
    statement = statement.offset(params.offset).limit(params.size)
    items = list((await session.exec(statement)).all())
    return items, total


async def get_conversation(
    session: AsyncSession, user: User, conversation_id: int
) -> Conversation:
    conversation = await session.get(Conversation, conversation_id)
    if conversation is None:
        raise NotFoundError("Conversation not found")
    _authorize(user, conversation)
    return conversation


async def list_messages(session: AsyncSession, conversation_id: int) -> list[Message]:
    statement = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.id)
    )
    return list((await session.exec(statement)).all())


async def get_conversation_detail(
    session: AsyncSession, user: User, conversation_id: int
) -> tuple[Conversation, list[Message]]:
    conversation = await get_conversation(session, user, conversation_id)
    messages = await list_messages(session, conversation.id)
    return conversation, messages


async def delete_conversation(
    session: AsyncSession, user: User, conversation_id: int
) -> None:
    conversation = await get_conversation(session, user, conversation_id)
    await session.delete(conversation)
    await session.commit()


async def create_exchange(
    session: AsyncSession, user: User, conversation_id: int, data: MessageCreate
) -> tuple[Message, Message]:
    conversation = await get_conversation(session, user, conversation_id)
    history = [
        {"role": message.role.value, "content": message.content}
        for message in await list_messages(session, conversation.id)
    ]

    user_message = Message(
        conversation_id=conversation.id,
        role=MessageRole.USER,
        content=data.content,
    )
    session.add(user_message)
    await session.commit()
    await session.refresh(user_message)

    reply_text, sources, _ = await generate_reply(
        session, user, [*history, {"role": "user", "content": data.content}]
    )

    assistant_message = Message(
        conversation_id=conversation.id,
        role=MessageRole.ASSISTANT,
        content=reply_text,
        sources=sources,
    )
    conversation.updated_at = datetime.now(UTC)
    session.add(assistant_message)
    session.add(conversation)
    await session.commit()
    await session.refresh(assistant_message)
    return user_message, assistant_message
