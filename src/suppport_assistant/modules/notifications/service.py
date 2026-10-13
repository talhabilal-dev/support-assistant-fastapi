import asyncio
import logging
from pathlib import Path

import resend
from jinja2 import Environment, FileSystemLoader, select_autoescape

from suppport_assistant.core.config import settings
from suppport_assistant.modules.tickets.models import Ticket
from suppport_assistant.modules.users.models import User

logger = logging.getLogger("suppport_assistant.notifications")

TEMPLATES_DIR = Path(__file__).parent / "templates"
_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html"]),
)


def render_template(name: str, context: dict) -> str:
    return _env.get_template(name).render(**context)


def _send_sync(to: str, subject: str, html: str) -> None:
    resend.api_key = settings.resend_api_key
    resend.Emails.send(
        {"from": settings.email_from, "to": to, "subject": subject, "html": html}
    )


async def send_email(to: str, subject: str, html: str) -> None:
    if not settings.resend_api_key:
        logger.info("[dry-run] email to=%s subject=%r", to, subject)
        return
    await asyncio.to_thread(_send_sync, to, subject, html)


async def send_welcome_email(user: User) -> None:
    html = render_template("welcome.html", {"full_name": user.full_name or user.email})
    await send_email(user.email, "Welcome to Suppport Assistant", html)


async def send_ticket_created_email(user: User, ticket: Ticket) -> None:
    html = render_template("ticket_created.html", {"ticket": ticket})
    await send_email(user.email, f"Support ticket #{ticket.id} created", html)


async def send_ticket_status_changed_email(user: User, ticket: Ticket) -> None:
    html = render_template("ticket_status_changed.html", {"ticket": ticket})
    await send_email(
        user.email,
        f"Support ticket #{ticket.id} is now {ticket.status.value}",
        html,
    )


async def send_email_verification(user: User, token: str) -> None:
    html = render_template(
        "verify_email.html",
        {"full_name": user.full_name or user.email, "token": token},
    )
    await send_email(user.email, "Verify your email address", html)


async def send_password_reset_email(user: User, token: str) -> None:
    html = render_template(
        "reset_password.html",
        {"full_name": user.full_name or user.email, "token": token},
    )
    await send_email(user.email, "Reset your password", html)
