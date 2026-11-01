import logging
from dataclasses import dataclass, field

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.supabase import get_supabase_auth_client

logger = logging.getLogger(__name__)
bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedUser:
    id: str
    access_token: str = field(repr=False)
    email: str | None = None


def require_authenticated_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid Supabase access token is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        client = get_supabase_auth_client()
    except Exception as error:
        logger.error("Supabase auth client initialization failed (%s)", type(error).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is unavailable. Check the backend Supabase configuration.",
        ) from None
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is unavailable. Check the backend Supabase configuration.",
        )

    try:
        response = client.auth.get_user(credentials.credentials)
        user = response.user
        user_id = getattr(user, "id", None)
        if not isinstance(user_id, str) or not user_id:
            raise ValueError("Supabase returned no user identity.")
        email = getattr(user, "email", None)
        return AuthenticatedUser(
            id=user_id,
            access_token=credentials.credentials,
            email=email if isinstance(email, str) else None,
        )
    except Exception as error:
        logger.info("Supabase access-token verification failed (%s)", type(error).__name__)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session is invalid or expired. Sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
