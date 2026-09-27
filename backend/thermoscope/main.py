from collections.abc import Callable
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import FastAPI, Header, Path, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from thermoscope.assessment import observation_assessment, observation_timeline
from thermoscope.config import DataMode, Settings
from thermoscope.context import facilities_geojson, observation_context
from thermoscope.database import check_readiness
from thermoscope.events import event_detail, list_events
from thermoscope.firms import IngestError
from thermoscope.labels import (
    EVIDENCE_KINDS,
    SOURCE_LABELS,
    SOURCE_LOCATIONS,
    SUBTYPES,
    CaseChanged,
    CaseSetSuperseded,
    list_case_sets,
    models_list,
    review_case,
    review_queue,
    submit_review,
)
from thermoscope.observations import catalog, list_observations, query_params
from thermoscope.regions import Bounds, Product
from thermoscope.reviewers import SIGN_IN, authenticate, bearer_token, reviewers_configured


class AssessmentBasis(StrEnum):
    RETROSPECTIVE = "RETROSPECTIVE"
    OPERATIONAL = "OPERATIONAL"


CASE_SET = Path(pattern="^[a-z0-9][a-z0-9_-]{2,60}$|^[0-9a-f-]{36}$")
AUTHORIZATION = Header(max_length=300)


class EvidenceIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: str = Field(min_length=8, max_length=500)
    kind: Literal[EVIDENCE_KINDS]
    observed_on: date | None = None
    licence: str | None = Field(default=None, max_length=120)


class ReviewIn(BaseModel):
    """Evidence items replace the earlier bare-link list (ADR-021). The reviewer is the signed-in
    account (ADR-023); a body that names a reviewer is rejected."""

    model_config = ConfigDict(extra="forbid")
    case_id: str = Field(pattern="^[0-9a-f]{64}$")
    source_label: Literal[SOURCE_LABELS]
    industrial_subtype: Literal[SUBTYPES] | None = None
    certainty: Literal["HIGH", "MEDIUM", "LOW"]
    source_location: Literal[SOURCE_LOCATIONS] | None = None
    # The role shown with the case (`your_role`); refused with 409 if the case changed since.
    expected_role: Literal["REVIEWER", "ADJUDICATOR"]
    evidence: list[EvidenceIn] = Field(default_factory=list, max_length=5)
    notes: str | None = Field(default=None, max_length=2000)


def create_app(settings: Settings | None = None, probe: Callable | None = None) -> FastAPI:
    config = settings if settings is not None else Settings()
    readiness_probe = probe if probe is not None else lambda: check_readiness(config)
    app = FastAPI(title="ThermoScope", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.allowed_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Authorization"],
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

    def withheld(request):
        return error_response(
            request,
            "WITHHELD_ON_REVIEW_SERVER",
            "Withheld on the blind-review server: no automated assessments or label progress.",
            403,
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
            "stage": "LABELS_AND_MODEL_PIPELINE",
            "data_mode": config.app_data_mode.value,
            "ingestion_status": "MANUAL_CLI",
            "classifier_status": "NOT_SERVED_AWAITING_REVIEWED_LABELS",
            "rules_status": "HEURISTIC_RULES_UNCALIBRATED",
            "review_only": config.review_only,
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

    @app.get("/api/v1/observations/{observation_id}/context")
    def context(
        request: Request,
        observation_id: Annotated[str, Path(pattern="^[0-9a-f]{64}$")],
        data_mode: DataMode = config.app_data_mode,
    ):
        try:
            result = observation_context(config, observation_id, data_mode)
        except (SQLAlchemyError, ValueError):
            return error_response(
                request, "DATA_UNAVAILABLE", "The stored-data service is not ready."
            )
        if result is None:
            return error_response(
                request, "NOT_FOUND", "No observation with that ID exists in this data mode.", 404
            )
        return result

    @app.get("/api/v1/events")
    def events(
        request: Request,
        bbox: Annotated[str, Query(max_length=120)],
        start_date: date,
        end_date: date,
        data_mode: DataMode = config.app_data_mode,
        product: Product = Product.NOAA20,
        limit: int = Query(default=200, ge=1, le=500),
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
            return list_events(config, bounds, start_date, end_date, data_mode, product, limit)
        except (SQLAlchemyError, ValueError):
            return error_response(
                request, "DATA_UNAVAILABLE", "The stored-data service is not ready."
            )

    @app.get("/api/v1/events/{event_id}")
    def event(
        request: Request,
        event_id: Annotated[str, Path(pattern="^[0-9a-f]{64}$")],
        data_mode: DataMode = config.app_data_mode,
    ):
        try:
            result = event_detail(config, event_id, data_mode)
        except (SQLAlchemyError, ValueError):
            return error_response(
                request, "DATA_UNAVAILABLE", "The stored-data service is not ready."
            )
        if result is None:
            return error_response(
                request, "NOT_FOUND", "No event with that ID exists in this data mode.", 404
            )
        return result

    @app.get("/api/v1/observations/{observation_id}/assessment")
    def assessment(
        request: Request,
        observation_id: Annotated[str, Path(pattern="^[0-9a-f]{64}$")],
        data_mode: DataMode = config.app_data_mode,
        basis: AssessmentBasis = AssessmentBasis.RETROSPECTIVE,
        as_of: datetime | None = None,
    ):
        if config.review_only:
            return withheld(request)
        if as_of is not None and (as_of.tzinfo is None or as_of > datetime.now(UTC)):
            return error_response(
                request, "INVALID_QUERY", "as_of needs a timezone and cannot be in the future.", 422
            )
        try:
            result = observation_assessment(config, observation_id, data_mode, as_of, basis.value)
        except ValueError:
            return error_response(
                request, "INVALID_QUERY", "as_of cannot precede the observation.", 422
            )
        except SQLAlchemyError:
            return error_response(
                request, "DATA_UNAVAILABLE", "The stored-data service is not ready."
            )
        if result is None:
            return error_response(
                request, "NOT_FOUND", "No observation with that ID exists in this data mode.", 404
            )
        return result

    @app.get("/api/v1/observations/{observation_id}/timeline")
    def timeline(
        request: Request,
        observation_id: Annotated[str, Path(pattern="^[0-9a-f]{64}$")],
        data_mode: DataMode = config.app_data_mode,
        basis: AssessmentBasis = AssessmentBasis.RETROSPECTIVE,
        days: int = Query(default=180, ge=7, le=180),
    ):
        if config.review_only:
            return withheld(request)
        try:
            result = observation_timeline(config, observation_id, data_mode, days, basis.value)
        except (SQLAlchemyError, ValueError):
            return error_response(
                request, "DATA_UNAVAILABLE", "The stored-data service is not ready."
            )
        if result is None:
            return error_response(
                request, "NOT_FOUND", "No observation with that ID exists in this data mode.", 404
            )
        return result

    @app.get("/api/v1/map/facilities.geojson")
    def facilities(
        request: Request,
        bbox: Annotated[str, Query(max_length=120)],
        data_mode: DataMode = config.app_data_mode,
    ):
        try:
            bounds = Bounds.parse(bbox)
        except ValueError:
            return error_response(
                request, "INVALID_QUERY", "Use bounds up to 5 degrees per axis.", 422
            )
        try:
            return facilities_geojson(config, bounds, data_mode)
        except (SQLAlchemyError, ValueError):
            return error_response(
                request, "DATA_UNAVAILABLE", "The stored-data service is not ready."
            )

    def unavailable(request):
        return error_response(request, "DATA_UNAVAILABLE", "The stored-data service is not ready.")

    def unauthorized(request):
        return error_response(
            request, "UNAUTHORIZED", "Sign in with your personal reviewer token.", 401
        )

    def signed_in(authorization: str | None) -> dict | None:
        """The active reviewer account for this request (raises SQLAlchemyError/ValueError when
        the database is unavailable or not configured)."""
        token = bearer_token(authorization)
        return None if token is None else authenticate(config, token)

    @app.get("/api/v1/annotation/case-sets")
    def case_sets(request: Request):
        try:
            return {
                "case_sets": list_case_sets(config),
                "sign_in": SIGN_IN,
                "review_enabled": reviewers_configured(config),
            }
        except (SQLAlchemyError, ValueError):
            return unavailable(request)

    @app.get("/api/v1/annotation/me")
    def me(request: Request, authorization: Annotated[str | None, AUTHORIZATION] = None):
        try:
            reviewer = signed_in(authorization)
        except (SQLAlchemyError, ValueError):
            return unavailable(request)
        if reviewer is None:
            return unauthorized(request)
        return {"name": reviewer["name"], "can_adjudicate": reviewer["can_adjudicate"],
                "sign_in": SIGN_IN}  # fmt: skip

    @app.get("/api/v1/annotation/{case_set}/queue")
    def queue(
        request: Request,
        case_set: Annotated[str, CASE_SET],
        authorization: Annotated[str | None, AUTHORIZATION] = None,
        limit: int = Query(default=20, ge=1, le=100),
    ):
        try:
            reviewer = signed_in(authorization)
            if reviewer is None:
                return unauthorized(request)
            return review_queue(config, case_set, reviewer, limit)
        except IngestError:
            return error_response(request, "NOT_FOUND", "No case set with that name.", 404)
        except (SQLAlchemyError, ValueError):
            return unavailable(request)

    @app.get("/api/v1/annotation/{case_set}/cases/{case_id}")
    def annotation_case(
        request: Request,
        case_set: Annotated[str, CASE_SET],
        case_id: Annotated[str, Path(pattern="^[0-9a-f]{64}$")],
        authorization: Annotated[str | None, AUTHORIZATION] = None,
    ):
        try:
            reviewer = signed_in(authorization)
            if reviewer is None:
                return unauthorized(request)
            result = review_case(config, case_set, case_id, reviewer)
        except IngestError:
            result = None
        except (SQLAlchemyError, ValueError):
            return unavailable(request)
        if result is None:
            return error_response(request, "NOT_FOUND", "No such case in this case set.", 404)
        return result

    @app.post("/api/v1/annotation/{case_set}/reviews", status_code=201)
    def create_review(
        request: Request,
        case_set: Annotated[str, CASE_SET],
        review: ReviewIn,
        authorization: Annotated[str | None, AUTHORIZATION] = None,
    ):
        if bearer_token(authorization) is None:
            return unauthorized(request)
        try:
            reviewer = signed_in(authorization)
        except (SQLAlchemyError, ValueError):
            return unavailable(request)
        if reviewer is None:
            return unauthorized(request)
        try:
            return submit_review(config, case_set, review.model_dump(mode="json"), reviewer)
        except IngestError:
            return error_response(request, "NOT_FOUND", "No case set with that name.", 404)
        except LookupError:
            return error_response(request, "NOT_FOUND", "No such case in this case set.", 404)
        except PermissionError:
            return unauthorized(request)
        except CaseChanged as error:
            return error_response(request, "CASE_CHANGED", str(error), 409)
        except CaseSetSuperseded as error:
            return error_response(request, "CASE_SET_SUPERSEDED", str(error), 409)
        except ValueError as error:
            return error_response(request, "INVALID_REVIEW", str(error), 422)
        except IntegrityError:
            return error_response(
                request, "CONFLICT", "This review was already recorded; reload the case.", 409
            )
        except SQLAlchemyError:
            return unavailable(request)

    @app.get("/api/v1/models")
    def models(request: Request):
        try:
            return {"models": models_list(config)}
        except SQLAlchemyError:
            return unavailable(request)

    return app


app = create_app()
