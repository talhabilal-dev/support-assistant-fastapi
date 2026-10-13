from fastapi import APIRouter, status

from suppport_assistant.core.pagination import Page, PageParamsDep
from suppport_assistant.db.session import SessionDep
from suppport_assistant.modules.auth.dependencies import CurrentUser
from suppport_assistant.modules.conversations.models import Conversation
from suppport_assistant.modules.conversations.schemas import (
    ChatResponse,
    ConversationCreate,
    ConversationDetail,
    ConversationRead,
    MessageCreate,
    MessageRead,
)
from suppport_assistant.modules.conversations.service import (
    create_conversation,
    create_exchange,
    delete_conversation,
    get_conversation_detail,
    list_conversations,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
async def create(
    payload: ConversationCreate, current_user: CurrentUser, session: SessionDep
) -> Conversation:
    return await create_conversation(session, current_user, payload)


@router.get("", response_model=Page[ConversationRead])
async def list_all(
    params: PageParamsDep, current_user: CurrentUser, session: SessionDep
) -> Page[ConversationRead]:
    items, total = await list_conversations(session, current_user, params)
    return Page(
        items=[ConversationRead.model_validate(item) for item in items],
        total=total,
        page=params.page,
        size=params.size,
    )


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get(
    conversation_id: int, current_user: CurrentUser, session: SessionDep
) -> ConversationDetail:
    conversation, messages = await get_conversation_detail(
        session, current_user, conversation_id
    )
    return ConversationDetail(
        id=conversation.id,
        user_id=conversation.user_id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[MessageRead.model_validate(message) for message in messages],
    )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    conversation_id: int, current_user: CurrentUser, session: SessionDep
) -> None:
    await delete_conversation(session, current_user, conversation_id)


@router.post(
    "/{conversation_id}/messages",
    response_model=ChatResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_message(
    conversation_id: int,
    payload: MessageCreate,
    current_user: CurrentUser,
    session: SessionDep,
) -> ChatResponse:
    user_message, assistant_message = await create_exchange(
        session, current_user, conversation_id, payload
    )
    return ChatResponse(
        user_message=MessageRead.model_validate(user_message),
        assistant_message=MessageRead.model_validate(assistant_message),
    )
