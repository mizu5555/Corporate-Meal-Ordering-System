from fastapi import APIRouter, status

from backend.core.errors import CodedHTTPException
from backend.core.security import create_access_token, hash_password, verify_password
from backend.db.connection import get_connection
from backend.schemas.auth import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])

# Constant-time placeholder so verify_password always runs even when the account
# does not exist, keeping login latency uniform (mitigates username enumeration).
# Computed at import so no bcrypt hash literal lives in the source.
_DUMMY_HASH = hash_password("timing-attack-placeholder")


def _fetch_user(email: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT
                u.id,
                u.email,
                u.display_name,
                u.password_hash,
                u.is_active,
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

    if not user["is_active"]:
        raise CodedHTTPException(
            status_code=403,
            code="account_disabled",
            detail="This account has been disabled",
        )

    jwt_data: dict = {"sub": str(user["id"]), "role": user["role"]}
    if user["vendor_id"] is not None:
        jwt_data["vendor_id"] = user["vendor_id"]

    return TokenResponse(
        access_token=create_access_token(jwt_data),
        user_id=user["id"],
        role=user["role"],
        display_name=user["display_name"],
        vendor_id=user["vendor_id"],
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest) -> TokenResponse:
    if len(payload.password) < 8:
        raise CodedHTTPException(
            status_code=422,
            code="password_too_short",
            detail="Password must be at least 8 characters",
        )

    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE email = %s", (payload.email,)
        ).fetchone()
        if existing:
            raise CodedHTTPException(
                status_code=409,
                code="email_taken",
                detail="An account with this email already exists",
            )

        row = conn.execute(
            """
            INSERT INTO users (email, display_name, role_id, password_hash, badge_code)
            SELECT %s, %s, r.id, %s,
                   CASE WHEN r.name = 'employee'
                        THEN 'EMP-' || LPAD(nextval('employee_badge_seq')::text, 4, '0')
                        ELSE NULL END
            FROM roles r
            WHERE r.name = %s
            RETURNING id, badge_code
            """,
            (payload.email, payload.display_name, hash_password(payload.password), payload.role),
        ).fetchone()

    user = _fetch_user(payload.email)
    jwt_data: dict = {"sub": str(user["id"]), "role": user["role"]}
    return TokenResponse(
        access_token=create_access_token(jwt_data),
        user_id=user["id"],
        role=user["role"],
        display_name=user["display_name"],
        vendor_id=None,
        badge_code=row["badge_code"],
    )
