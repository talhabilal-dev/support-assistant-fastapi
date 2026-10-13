from datetime import UTC, datetime

from sqlalchemy import func, or_
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from suppport_assistant.core.errors import NotFoundError, PermissionDeniedError
from suppport_assistant.core.pagination import PageParams
from suppport_assistant.modules.tickets.models import Ticket
from suppport_assistant.modules.tickets.schemas import TicketCreate, TicketUpdate
from suppport_assistant.modules.users.models import User


def _authorize(user: User, ticket: Ticket) -> None:
    if (
        user.is_superuser
        or ticket.created_by_id == user.id
        or ticket.assignee_id == user.id
    ):
        return
    raise PermissionDeniedError()


async def create_ticket(
    session: AsyncSession, user: User, data: TicketCreate
) -> Ticket:
    ticket = Ticket(
        subject=data.subject,
        description=data.description,
        priority=data.priority,
        created_by_id=user.id,
    )
    session.add(ticket)
    await session.commit()
    await session.refresh(ticket)
    return ticket


async def list_tickets(
    session: AsyncSession, user: User, params: PageParams
) -> tuple[list[Ticket], int]:
    statement = select(Ticket).order_by(Ticket.created_at.desc())
    count_statement = select(func.count()).select_from(Ticket)

    if not user.is_superuser:
        visible = or_(Ticket.created_by_id == user.id, Ticket.assignee_id == user.id)
        statement = statement.where(visible)
        count_statement = count_statement.where(visible)

    total = (await session.exec(count_statement)).one()
    statement = statement.offset(params.offset).limit(params.size)
    items = list((await session.exec(statement)).all())
    return items, total


async def get_ticket(session: AsyncSession, user: User, ticket_id: int) -> Ticket:
    ticket = await session.get(Ticket, ticket_id)
    if ticket is None:
        raise NotFoundError("Ticket not found")
    _authorize(user, ticket)
    return ticket


async def update_ticket(
    session: AsyncSession, user: User, ticket_id: int, data: TicketUpdate
) -> Ticket:
    ticket = await get_ticket(session, user, ticket_id)

    changes = data.model_dump(exclude_unset=True)
    # Only assignee_id may be explicitly nulled (to unassign); ignore other nulls.
    changes = {
        key: value
        for key, value in changes.items()
        if value is not None or key == "assignee_id"
    }
    for key, value in changes.items():
        setattr(ticket, key, value)

    ticket.updated_at = datetime.now(UTC)
    session.add(ticket)
    await session.commit()
    await session.refresh(ticket)
    return ticket


async def delete_ticket(session: AsyncSession, user: User, ticket_id: int) -> None:
    ticket = await get_ticket(session, user, ticket_id)
    await session.delete(ticket)
    await session.commit()
