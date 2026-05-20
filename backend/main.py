from contextlib import asynccontextmanager
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from backend.core.config import settings
from backend.core.errors import install_error_handler
from backend.core.vendor_identity import get_vendor_profile_repository
from backend.db.migrate import run_migrations
from backend.repositories.vendor_profile_repository import VendorRecord
from backend.routes import (
    admin_vendors,
    committee_reviews,
    employee_ordering,
    health,
    vendor_categories,
    vendor_menu,
    vendor_profile,
)


_logger = logging.getLogger(__name__)

# Dedicated bot vendor used by the k6 post-deploy smoke in Jenkinsfile.staging.
# Kept far away from auto-incremented human application IDs so it cannot collide
# with — or be mistaken for — a real vendor created via the normal application
# + admin-approval flow.
_K6_SMOKE_VENDOR_ID = 99
_K6_SMOKE_VENDOR_NAME = "K6 Smoke Vendor"


def _seed_k6_smoke_vendor() -> None:
    """Seed the dedicated bot vendor used by the Jenkins staging k6 smoke.

    Routes through `get_vendor_profile_repository()` so the seed lands in the
    active repo — in-memory when DATABASE_URL is unset (local / unit tests),
    Postgres when it is set (staging / prod). Postgres seed uses INSERT ON
    CONFLICT DO UPDATE so re-running on every startup is idempotent.

    Guarded by env var so prod (whose compose override does NOT set it) is
    untouched. The warning log is intentional: if this line ever shows up in
    prod logs, someone copy-pasted the staging compose by mistake.
    """
    if os.getenv("SEED_K6_SMOKE_VENDOR") != "1":
        return
    _logger.warning(
        "seeding K6 smoke vendor (id=%d) — must not run in prod",
        _K6_SMOKE_VENDOR_ID,
    )
    repo = get_vendor_profile_repository()
    repo.seed(
        VendorRecord(
            id=_K6_SMOKE_VENDOR_ID,
            name=_K6_SMOKE_VENDOR_NAME,
            status="approved",
        )
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()
    _seed_k6_smoke_vendor()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        root_path=os.getenv("ROOT_PATH", ""),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    install_error_handler(app)

    app.include_router(health.router)
    app.include_router(admin_vendors.router)
    app.include_router(committee_reviews.router)
    app.include_router(vendor_profile.router)
    app.include_router(vendor_categories.router)
    app.include_router(vendor_menu.router)
    app.include_router(employee_ordering.router)

    Instrumentator(should_instrument_requests_inprogress=True).instrument(app).expose(app)
    return app


app = create_app()
