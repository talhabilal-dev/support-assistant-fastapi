import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from pwdlib import PasswordHash

from suppport_assistant.core.config import settings
from suppport_assistant.core.errors import AuthenticationError

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"

_password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return _password_hash.verify(password, hashed_password)


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def _create_token(
    subject: str, session_token: str, token_type: str, expires_in: timedelta
) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "sid": session_token,
        "type": token_type,
        "iat": now,
        "exp": now + expires_in,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str, session_token: str) -> str:
    return _create_token(
        subject,
        session_token,
        ACCESS_TOKEN_TYPE,
        timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(subject: str, session_token: str) -> str:
    return _create_token(
        subject,
        session_token,
        REFRESH_TOKEN_TYPE,
        timedelta(days=settings.refresh_token_expire_days),
    )


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(
            token, settings.secret_key, algorithms=[settings.jwt_algorithm]
        )
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Invalid or expired token") from exc


def decode_access_token(token: str) -> dict[str, Any]:
    claims = decode_token(token)
    if claims.get("type") != ACCESS_TOKEN_TYPE:
        raise AuthenticationError("Invalid token type")
    return claims


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.secret_key, salt="suppport-assistant")


def create_action_token(email: str, purpose: str) -> str:
    return _serializer().dumps({"email": email, "purpose": purpose})


def read_action_token(token: str, purpose: str, max_age: int) -> str:
    try:
        data = _serializer().loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired) as exc:
        raise AuthenticationError("Invalid or expired token") from exc
    if data.get("purpose") != purpose:
        raise AuthenticationError("Invalid token purpose")
    return data["email"]
