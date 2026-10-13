from fastapi import APIRouter, status

from suppport_assistant.db.session import SessionDep
from suppport_assistant.modules.auth.dependencies import CurrentUser
from suppport_assistant.modules.users.models import User
from suppport_assistant.modules.users.schemas import (
    PasswordChange,
    UserRead,
    UserUpdate,
)
from suppport_assistant.modules.users.service import change_password, update_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
async def read_profile(current_user: CurrentUser) -> User:
    return current_user


@router.patch("/me", response_model=UserRead)
async def update_profile(
    payload: UserUpdate, current_user: CurrentUser, session: SessionDep
) -> User:
    return await update_user(session, current_user, payload)


@router.post("/me/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password_route(
    payload: PasswordChange, current_user: CurrentUser, session: SessionDep
) -> None:
    await change_password(session, current_user, payload)
