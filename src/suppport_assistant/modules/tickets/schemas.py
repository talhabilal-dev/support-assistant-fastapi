from datetime import datetime

from pydantic import Field
from sqlmodel import SQLModel

from suppport_assistant.modules.tickets.models import TicketPriority, TicketStatus


class TicketCreate(SQLModel):
    subject: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    priority: TicketPriority = TicketPriority.MEDIUM


class TicketUpdate(SQLModel):
    subject: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1)
    status: TicketStatus | None = None
    priority: TicketPriority | None = None
    assignee_id: int | None = None


class TicketRead(SQLModel):
    id: int
    subject: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    created_by_id: int
    assignee_id: int | None
    created_at: datetime
    updated_at: datetime
