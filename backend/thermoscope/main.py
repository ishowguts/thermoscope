from collections.abc import Callable
from datetime import date
from typing import Annotated
from uuid import uuid4

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from thermoscope.config import DataMode, Settings
from thermoscope.database import check_readiness
from thermoscope.observations import catalog, list_observations, query_params
from thermoscope.regions import Bounds, Product


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

    def error_response(request, code, message, status=503):
        return JSONResponse(
            status_code=status,
            content={
                "code": code,
                "message": message,
                "request_id": request.state.request_id,
                "retryable": status == 503,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def invalid_query(request, error):
        return error_response(
            request, "INVALID_QUERY", "Check region, dates, mode and page limits.", 422
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
            "stage": "OBSERVATIONS",
            "data_mode": config.app_data_mode.value,
            "ingestion_status": "MANUAL_CLI",
            "classifier_status": "NOT_IMPLEMENTED",
            "observation_count": None,
            "last_acquisition_at": None,
        }

    @app.get("/api/v1/catalog")
    def regions(
        request: Request,
        data_mode: DataMode = config.app_data_mode,
        product: Product = Product.NOAA20,
    ):
        try:
            return catalog(config, data_mode, product)
        except (SQLAlchemyError, ValueError):
            return error_response(
                request, "DATA_UNAVAILABLE", "The stored-data service is not ready."
            )

    @app.get("/api/v1/observations")
    def observations(
        request: Request,
        bbox: Annotated[str, Query(max_length=120)],
        start_date: date,
        end_date: date,
        data_mode: DataMode = config.app_data_mode,
        product: Product = Product.NOAA20,
        limit: int = Query(default=100, ge=1, le=500),
        offset: int = Query(default=0, ge=0, le=10000),
    ):
        try:
            bounds = Bounds.parse(bbox)
            query_params(bounds, start_date, end_date, data_mode, product)
        except ValueError:
            return error_response(
                request,
                "INVALID_QUERY",
                "Use bounds up to 5 degrees per axis and a 1–31 day window.",
                422,
            )
        try:
            return list_observations(
                config, bounds, start_date, end_date, data_mode, product, limit, offset
            )
        except (SQLAlchemyError, ValueError):
            return error_response(
                request, "DATA_UNAVAILABLE", "The stored-data service is not ready."
            )

    return app


app = create_app()
