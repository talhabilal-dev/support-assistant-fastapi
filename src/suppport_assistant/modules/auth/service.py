from sqlmodel.ext.asyncio.session import AsyncSession

from suppport_assistant.core.config import settings
from suppport_assistant.core.errors import AuthenticationError
from suppport_assistant.core.security import (
    REFRESH_TOKEN_TYPE,
    create_access_token,
    create_action_token,
    create_refresh_token,
    decode_token,
    generate_session_token,
    hash_password,
    read_action_token,
    verify_password,
)
from suppport_assistant.modules.notifications.service import (
    send_email_verification,
    send_password_reset_email,
)
from suppport_assistant.modules.users.models import User
from suppport_assistant.modules.users.service import get_user_by_email, get_user_by_id

EMAIL_VERIFICATION_PURPOSE = "verify-email"
PASSWORD_RESET_PURPOSE = "reset-password"


def _issue_tokens(user: User, session_token: str) -> tuple[str, str]:
    return (
        create_access_token(str(user.id), session_token),
        create_refresh_token(str(user.id), session_token),
    )


async def authenticate(session: AsyncSession, email: str, password: str) -> User:
    user = await get_user_by_email(session, email)
    if user is None or not verify_password(password, user.hashed_password):
        raise AuthenticationError("Invalid email or password")
    if not user.is_active:
        raise AuthenticationError("User account is inactive")
    return user


async def start_session(session: AsyncSession, user: User) -> tuple[str, str]:
    session_token = generate_session_token()
    user.session_token = session_token
    session.add(user)
    await session.commit()
    return _issue_tokens(user, session_token)


async def end_session(session: AsyncSession, user: User) -> None:
    user.session_token = None
    session.add(user)
    await session.commit()


async def refresh_session(session: AsyncSession, refresh_token: str) -> tuple[str, str]:
    claims = decode_token(refresh_token)
    if claims.get("type") != REFRESH_TOKEN_TYPE:
        raise AuthenticationError("Invalid refresh token")

    subject = claims.get("sub")
    if subject is None:
        raise AuthenticationError("Invalid token payload")

    user = await get_user_by_id(session, int(subject))
    if user is None or not user.is_active:
        raise AuthenticationError("User not found or inactive")
    if not user.session_token or user.session_token != claims.get("sid"):
        raise AuthenticationError("Session is no longer valid")

    return _issue_tokens(user, user.session_token)


async def send_verification_email(user: User) -> None:
    token = create_action_token(user.email, EMAIL_VERIFICATION_PURPOSE)
    await send_email_verification(user, token)


async def verify_email(session: AsyncSession, token: str) -> User:
    email = read_action_token(
        token,
        EMAIL_VERIFICATION_PURPOSE,
        settings.email_verification_expire_minutes * 60,
    )
    user = await get_user_by_email(session, email)
    if user is None:
        raise AuthenticationError("User not found")

    user.is_verified = True
    session.add(user)
    await session.commit()
    return user


async def request_password_reset(session: AsyncSession, email: str) -> None:
    user = await get_user_by_email(session, email)
    if user is None:
        return

    token = create_action_token(user.email, PASSWORD_RESET_PURPOSE)
    await send_password_reset_email(user, token)


async def reset_password(session: AsyncSession, token: str, new_password: str) -> User:
    email = read_action_token(
        token,
        PASSWORD_RESET_PURPOSE,
        settings.password_reset_expire_minutes * 60,
    )
    user = await get_user_by_email(session, email)
    if user is None:
        raise AuthenticationError("User not found")

    user.hashed_password = hash_password(new_password)
    # Invalidate any active session after a password reset.
    user.session_token = None
    session.add(user)
    await session.commit()
    return user
