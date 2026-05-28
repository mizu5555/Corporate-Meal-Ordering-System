from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from backend.core.config import settings
from backend.core.errors import install_error_handler
from backend.core.observability import RequestIDMiddleware, configure_logging
from backend.db.migrate import run_migrations
from backend.routes import (
    admin_users,
    admin_vendors,
    audit_logs,
    auth,
    committee_reviews,
    employee_ordering,
    health,
    notifications,
    vendor_application,
    vendor_categories,
    vendor_menu,
    vendor_orders,
    vendor_profile,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()
    yield


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(
        title=settings.app_name,
        root_path=os.getenv("ROOT_PATH", ""),
        lifespan=lifespan,
    )

    # RequestIDMiddleware before CORS so the response header survives CORS
    # rewrites and is the outermost wrapper that touches every response.
    app.add_middleware(RequestIDMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    install_error_handler(app)

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(admin_users.router)
    app.include_router(admin_vendors.router)
    app.include_router(committee_reviews.router)
    app.include_router(vendor_application.router)
    app.include_router(vendor_profile.router)
    app.include_router(vendor_categories.router)
    app.include_router(vendor_menu.router)
    app.include_router(vendor_orders.router)
    app.include_router(employee_ordering.router)
    app.include_router(notifications.router)
    app.include_router(audit_logs.router)

    Instrumentator(should_instrument_requests_inprogress=True).instrument(app).expose(app)
    return app


app = create_app()
