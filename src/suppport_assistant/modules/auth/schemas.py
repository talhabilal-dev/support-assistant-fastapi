from pydantic import EmailStr, Field
from sqlmodel import SQLModel


class LoginRequest(SQLModel):
    email: EmailStr
    password: str


class RefreshRequest(SQLModel):
    refresh_token: str


class TokenResponse(SQLModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class VerifyEmailRequest(SQLModel):
    token: str


class ForgotPasswordRequest(SQLModel):
    email: EmailStr


class ResetPasswordRequest(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)
