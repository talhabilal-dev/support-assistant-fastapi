from pydantic import EmailStr, Field
from sqlmodel import SQLModel


class UserCreate(SQLModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


class UserRead(SQLModel):
    id: int
    email: str
    full_name: str | None
    is_active: bool
    is_verified: bool
    is_superuser: bool


class UserUpdate(SQLModel):
    email: EmailStr | None = None
    full_name: str | None = Field(default=None, max_length=255)


class PasswordChange(SQLModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)
