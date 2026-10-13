from datetime import UTC, datetime
from enum import Enum, StrEnum

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, text
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _enum_column(enum_cls: type[Enum], name: str) -> Column:
    return Column(
        SAEnum(enum_cls, name=name, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )


class Conversation(SQLModel, table=True):
    __tablename__ = "conversations"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    title: str = Field(max_length=255)
    created_at: datetime = Field(
        default_factory=_utcnow, sa_type=DateTime(timezone=True)
    )
    updated_at: datetime = Field(
        default_factory=_utcnow, sa_type=DateTime(timezone=True)
    )


class Message(SQLModel, table=True):
    __tablename__ = "messages"

    id: int | None = Field(default=None, primary_key=True)
    conversation_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    role: MessageRole = Field(
        default=MessageRole.USER,
        sa_column=_enum_column(MessageRole, "messagerole"),
    )
    content: str
    sources: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, server_default=text("'[]'::json")),
    )
    created_at: datetime = Field(
        default_factory=_utcnow, sa_type=DateTime(timezone=True)
    )
