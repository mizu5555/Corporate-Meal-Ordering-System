from fastapi import APIRouter

from backend.core.errors import CodedHTTPException
from backend.core.security import create_access_token, verify_password
from backend.db.connection import get_connection
from backend.schemas.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])

_DUMMY_HASH = "$2b$12$DUMMYHASHFORINVALIDUSERXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"


def _fetch_user(email: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT
                u.id,
                u.email,
                u.password_hash,
                r.name  AS role,
                v.id    AS vendor_id
            FROM users u
            JOIN roles r ON r.id = u.role_id
            LEFT JOIN vendors v
                ON v.owner_user_id = u.id
                AND r.name = 'vendor_manager'
                AND v.status = 'approved'
            WHERE u.email = %s
            """,
            (email,),
        ).fetchone()
    return dict(row) if row else None


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    user = _fetch_user(payload.email)

    stored_hash = user["password_hash"] if (user and user["password_hash"]) else _DUMMY_HASH
    password_ok = verify_password(payload.password, stored_hash)

    if not password_ok or user is None or not user["password_hash"]:
        raise CodedHTTPException(
            status_code=401,
            code="invalid_credentials",
            detail="Invalid email or password",
        )

    jwt_data: dict = {"sub": str(user["id"]), "role": user["role"]}
    if user["vendor_id"] is not None:
        jwt_data["vendor_id"] = user["vendor_id"]

    return TokenResponse(
        access_token=create_access_token(jwt_data),
        user_id=user["id"],
        role=user["role"],
        vendor_id=user["vendor_id"],
    )
