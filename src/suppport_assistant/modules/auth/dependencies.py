from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from suppport_assistant.core.errors import AuthenticationError, PermissionDeniedError
from suppport_assistant.core.security import decode_access_token
from suppport_assistant.db.session import SessionDep
from suppport_assistant.modules.users.models import User
from suppport_assistant.modules.users.service import get_user_by_id

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: SessionDep,
) -> User:
    if credentials is None:
        raise AuthenticationError("Missing authentication credentials")

    claims = decode_access_token(credentials.credentials)
    subject = claims.get("sub")
    if subject is None:
        raise AuthenticationError("Invalid token payload")

    user = await get_user_by_id(session, int(subject))
    if user is None or not user.is_active:
        raise AuthenticationError("User not found or inactive")
    if not user.session_token or user.session_token != claims.get("sid"):
        raise AuthenticationError("Session is no longer valid")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_current_superuser(current_user: CurrentUser) -> User:
    if not current_user.is_superuser:
        raise PermissionDeniedError("Superuser privileges are required")
    return current_user


SuperUser = Annotated[User, Depends(get_current_superuser)]
