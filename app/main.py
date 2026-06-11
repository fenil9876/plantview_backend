"""FastAPI application entrypoint."""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import (
    analytics,
    audit,
    auth,
    batches,
    design,
    health,
    inventory,
    machines,
    templates,
    users,
)
from app.core.config import settings
from app.services.exceptions import ServiceError


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        debug=settings.DEBUG,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(ServiceError)
    async def _service_error_handler(_: Request, exc: ServiceError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    # Routers
    app.include_router(health.router)
    app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
    app.include_router(users.router, prefix=settings.API_V1_PREFIX)
    app.include_router(machines.router, prefix=settings.API_V1_PREFIX)
    app.include_router(templates.router, prefix=settings.API_V1_PREFIX)
    app.include_router(batches.router, prefix=settings.API_V1_PREFIX)
    app.include_router(audit.router, prefix=settings.API_V1_PREFIX)
    app.include_router(analytics.router, prefix=settings.API_V1_PREFIX)
    app.include_router(inventory.router, prefix=settings.API_V1_PREFIX)
    app.include_router(design.color_router, prefix=settings.API_V1_PREFIX)
    app.include_router(design.design_router, prefix=settings.API_V1_PREFIX)

    @app.get("/")
    def root() -> dict:
        return {"name": settings.PROJECT_NAME, "docs": "/docs"}

    return app


app = create_app()
