from collections.abc import Callable
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from thermoscope.config import Settings
from thermoscope.database import check_readiness


def create_app(settings: Settings | None = None, probe: Callable | None = None) -> FastAPI:
    config = settings if settings is not None else Settings()
    readiness_probe = probe if probe is not None else lambda: check_readiness(config)
    app = FastAPI(title="ThermoScope", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.allowed_origins,
        allow_methods=["GET"],
        allow_headers=["Content-Type"],
        expose_headers=["X-Request-ID"],
    )

    @app.middleware("http")
    async def request_id(request: Request, call_next):
        request.state.request_id = str(uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.get("/health/live")
    def live():
        return {"status": "ok"}

    @app.get("/health/ready")
    def ready(request: Request):
        checks = readiness_probe()
        if all(value == "ok" for value in checks.values()):
            return {"status": "ok", "checks": checks}
        return JSONResponse(
            status_code=503,
            content={
                "status": "unavailable",
                "checks": checks,
                "code": "DEPENDENCY_NOT_READY",
                "message": "The database or required schema is not ready.",
                "request_id": request.state.request_id,
                "retryable": True,
            },
        )

    @app.get("/api/v1/status")
    def status():
        return {
            "stage": "FOUNDATION",
            "data_mode": config.app_data_mode.value,
            "ingestion_status": "NOT_IMPLEMENTED",
            "classifier_status": "NOT_IMPLEMENTED",
            "observation_count": None,
            "last_acquisition_at": None,
        }

    return app


app = create_app()
