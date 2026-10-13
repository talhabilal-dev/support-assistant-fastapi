import asyncio
import getpass
import os
import sys

from sqlmodel import select

from suppport_assistant.core.security import hash_password
from suppport_assistant.db.session import session_factory
from suppport_assistant.modules.users.models import User


async def _create_admin(email: str, password: str) -> None:
    async with session_factory() as session:
        existing = (await session.exec(select(User).where(User.email == email))).first()

        if existing is not None:
            existing.is_superuser = True
            existing.is_active = True
            existing.is_verified = True
            session.add(existing)
            await session.commit()
            print(f"Promoted existing user {email} to superuser.")
            return

        session.add(
            User(
                email=email,
                hashed_password=hash_password(password),
                is_superuser=True,
                is_verified=True,
            )
        )
        await session.commit()
        print(f"Created superuser {email}.")


def create_admin() -> None:
    email = os.environ.get("ADMIN_EMAIL") or input("Admin email: ").strip()
    password = os.environ.get("ADMIN_PASSWORD") or getpass.getpass("Admin password: ")

    if not email or not password:
        print("Both email and password are required.", file=sys.stderr)
        raise SystemExit(1)

    asyncio.run(_create_admin(email, password))
