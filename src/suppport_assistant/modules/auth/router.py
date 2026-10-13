from fastapi import APIRouter, BackgroundTasks, Request, status

from suppport_assistant.core.config import settings
from suppport_assistant.core.ratelimit import limiter
from suppport_assistant.db.session import SessionDep
from suppport_assistant.modules.auth.dependencies import CurrentUser
from suppport_assistant.modules.auth.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    ResetPasswordRequest,
    TokenResponse,
    VerifyEmailRequest,
)
from suppport_assistant.modules.auth.service import (
    authenticate,
    end_session,
    refresh_session,
    request_password_reset,
    reset_password,
    send_verification_email,
    start_session,
    verify_email,
)
from suppport_assistant.modules.notifications.service import send_welcome_email
from suppport_assistant.modules.users.models import User
from suppport_assistant.modules.users.schemas import UserCreate, UserRead
from suppport_assistant.modules.users.service import create_user

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_response(access_token: str, refresh_token: str) -> TokenResponse:
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def register(
    request: Request,
    payload: UserCreate,
    background_tasks: BackgroundTasks,
    session: SessionDep,
) -> User:
    user = await create_user(session, payload)
    background_tasks.add_task(send_welcome_email, user)
    background_tasks.add_task(send_verification_email, user)
    return user


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request, payload: LoginRequest, session: SessionDep
) -> TokenResponse:
    user = await authenticate(session, payload.email, payload.password)
    access_token, refresh_token = await start_session(session, user)
    return _token_response(access_token, refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, session: SessionDep) -> TokenResponse:
    access_token, refresh_token = await refresh_session(session, payload.refresh_token)
    return _token_response(access_token, refresh_token)


@router.post("/verify-email", response_model=UserRead)
async def verify_email_endpoint(
    payload: VerifyEmailRequest, session: SessionDep
) -> User:
    return await verify_email(session, payload.token)


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("3/minute")
async def forgot_password(
    request: Request, payload: ForgotPasswordRequest, session: SessionDep
) -> None:
    await request_password_reset(session, payload.email)


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password_endpoint(
    payload: ResetPasswordRequest, session: SessionDep
) -> None:
    await reset_password(session, payload.token, payload.new_password)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(current_user: CurrentUser, session: SessionDep) -> None:
    await end_session(session, current_user)
