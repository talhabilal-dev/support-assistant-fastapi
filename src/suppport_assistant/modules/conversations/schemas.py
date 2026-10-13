from datetime import datetime

from pydantic import Field
from sqlmodel import SQLModel

from suppport_assistant.modules.conversations.models import MessageRole


class ConversationCreate(SQLModel):
    title: str | None = Field(default=None, max_length=255)


class MessageCreate(SQLModel):
    content: str = Field(min_length=1)


class MessageRead(SQLModel):
    id: int
    conversation_id: int
    role: MessageRole
    content: str
    sources: list[str] = Field(default_factory=list)
    created_at: datetime


class ConversationRead(SQLModel):
    id: int
    user_id: int
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationRead):
    messages: list[MessageRead] = Field(default_factory=list)


class ChatResponse(SQLModel):
    user_message: MessageRead
    assistant_message: MessageRead
