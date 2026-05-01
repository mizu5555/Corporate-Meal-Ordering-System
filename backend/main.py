from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import settings
from backend.core.errors import install_error_handler
from backend.routes import admin_vendors, committee_reviews, health


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)

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
    return app


app = create_app()
