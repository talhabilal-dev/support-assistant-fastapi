from fastapi import APIRouter, BackgroundTasks, status

from suppport_assistant.core.pagination import Page, PageParamsDep
from suppport_assistant.db.session import SessionDep
from suppport_assistant.modules.auth.dependencies import CurrentUser
from suppport_assistant.modules.notifications.service import (
    send_ticket_created_email,
    send_ticket_status_changed_email,
)
from suppport_assistant.modules.tickets.models import Ticket
from suppport_assistant.modules.tickets.schemas import (
    TicketCreate,
    TicketRead,
    TicketUpdate,
)
from suppport_assistant.modules.tickets.service import (
    create_ticket,
    delete_ticket,
    get_ticket,
    list_tickets,
    update_ticket,
)

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", response_model=TicketRead, status_code=status.HTTP_201_CREATED)
async def create(
    payload: TicketCreate,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    session: SessionDep,
) -> Ticket:
    ticket = await create_ticket(session, current_user, payload)
    background_tasks.add_task(send_ticket_created_email, current_user, ticket)
    return ticket


@router.get("", response_model=Page[TicketRead])
async def list_all(
    params: PageParamsDep, current_user: CurrentUser, session: SessionDep
) -> Page[TicketRead]:
    items, total = await list_tickets(session, current_user, params)
    return Page(
        items=[TicketRead.model_validate(item) for item in items],
        total=total,
        page=params.page,
        size=params.size,
    )


@router.get("/{ticket_id}", response_model=TicketRead)
async def get(ticket_id: int, current_user: CurrentUser, session: SessionDep) -> Ticket:
    return await get_ticket(session, current_user, ticket_id)


@router.patch("/{ticket_id}", response_model=TicketRead)
async def update(
    ticket_id: int,
    payload: TicketUpdate,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    session: SessionDep,
) -> Ticket:
    previous_status = (await get_ticket(session, current_user, ticket_id)).status
    ticket = await update_ticket(session, current_user, ticket_id, payload)
    if payload.status is not None and ticket.status != previous_status:
        background_tasks.add_task(
            send_ticket_status_changed_email, current_user, ticket
        )
    return ticket


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    ticket_id: int, current_user: CurrentUser, session: SessionDep
) -> None:
    await delete_ticket(session, current_user, ticket_id)
