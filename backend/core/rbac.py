from typing import Annotated

from fastapi import Depends, Header, HTTPException, status


def get_current_user_role(x_user_role: Annotated[str | None, Header()] = None) -> str:
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
