from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from suppport_assistant.core.errors import AuthenticationError, ConflictError
from suppport_assistant.core.security import hash_password, verify_password
from suppport_assistant.modules.users.models import User
from suppport_assistant.modules.users.schemas import (
    PasswordChange,
    UserCreate,
    UserUpdate,
)


async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    result = await session.exec(statement)
    return result.first()


async def create_user(session: AsyncSession, data: UserCreate) -> User:
    if await get_user_by_email(session, data.email) is not None:
        raise ConflictError("Email is already registered")

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def update_user(session: AsyncSession, user: User, data: UserUpdate) -> User:
    changes = data.model_dump(exclude_unset=True)
    # An explicit null email would violate the NOT NULL constraint; ignore it.
    if changes.get("email") is None:
        changes.pop("email", None)

    new_email = changes.get("email")
    if new_email is not None and new_email != user.email:
        existing = await get_user_by_email(session, new_email)
        if existing is not None and existing.id != user.id:
            raise ConflictError("Email is already registered")

    for field, value in changes.items():
        setattr(user, field, value)

    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def change_password(
    session: AsyncSession, user: User, data: PasswordChange
) -> None:
    if not verify_password(data.current_password, user.hashed_password):
        raise AuthenticationError("Current password is incorrect")

    user.hashed_password = hash_password(data.new_password)
    session.add(user)
    await session.commit()
