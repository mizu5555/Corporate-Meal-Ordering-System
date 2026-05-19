from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from backend.core.security import decode_access_token


def get_current_user_role(
    request: Request,
    x_user_role: Annotated[str | None, Header()] = None,
) -> str:
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        payload = decode_access_token(auth[7:])
        if payload:
            return payload.get("role", "anonymous")
    return x_user_role or "anonymous"


def require_roles(*allowed_roles: str):
    def dependency(role: Annotated[str, Depends(get_current_user_role)]) -> str:
        if role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return role

    return dependency
