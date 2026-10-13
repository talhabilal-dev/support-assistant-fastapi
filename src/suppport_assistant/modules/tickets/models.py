from datetime import UTC, datetime
from enum import Enum, StrEnum

from sqlalchemy import Column, DateTime
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel


class TicketStatus(StrEnum):
    OPEN = "open"
    PENDING = "pending"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _enum_column(enum_cls: type[Enum], name: str) -> Column:
    # Store the enum *values* (e.g. "open") rather than the member names ("OPEN").
    return Column(
        SAEnum(enum_cls, name=name, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )


class Ticket(SQLModel, table=True):
    __tablename__ = "tickets"

    id: int | None = Field(default=None, primary_key=True)
    subject: str = Field(max_length=255)
    description: str
    status: TicketStatus = Field(
        default=TicketStatus.OPEN,
        sa_column=_enum_column(TicketStatus, "ticketstatus"),
    )
    priority: TicketPriority = Field(
        default=TicketPriority.MEDIUM,
        sa_column=_enum_column(TicketPriority, "ticketpriority"),
    )
    created_by_id: int = Field(foreign_key="users.id", index=True)
    assignee_id: int | None = Field(default=None, foreign_key="users.id", index=True)
    created_at: datetime = Field(
        default_factory=_utcnow, sa_type=DateTime(timezone=True)
    )
    updated_at: datetime = Field(
        default_factory=_utcnow, sa_type=DateTime(timezone=True)
    )
