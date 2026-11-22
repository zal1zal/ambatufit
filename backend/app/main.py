from contextlib import asynccontextmanager
from datetime import datetime, timezone
import uuid
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.db import init_db
from app.contexts.identity_access.api import router as identity_router
from app.contexts.personal_health_intelligence.api import router as health_router
from app.contexts.personal_health_intelligence.medication_api import router as medication_router
from app.contexts.personal_health_intelligence.knowledge_api import router as knowledge_router
from app.contexts.personal_health_intelligence.chat_api import router as chat_router
from app.contexts.personal_health_intelligence.plan_api import router as plan_router
from app.contexts.consultation_booking.api import router as consultation_router

ERROR_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    422: "UNPROCESSABLE_ENTITY",
    429: "RATE_LIMITED",
    502: "BAD_GATEWAY",
    503: "SERVICE_UNAVAILABLE",
}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="AmbatuFit STB Microservice",
    description="Core backend service for AmbatuFit AI-assisted personal health platform. Deployed on STB.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


@app.middleware("http")
async def request_id_and_headers_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", f"req-{uuid.uuid4().hex[:12]}")
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _error_response(request: Request, status_code: int, code: str, message: str) -> JSONResponse:
    request_id = getattr(request.state, "request_id", f"req-{uuid.uuid4().hex[:12]}")
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "request_id": request_id}},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return _error_response(
        request,
        exc.status_code,
        ERROR_CODES.get(exc.status_code, "HTTP_ERROR"),
        str(exc.detail),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    first_error = exc.errors()[0] if exc.errors() else {}
    msg = first_error.get("msg", "Format data masukan tidak valid.")
    loc = ".".join(str(part) for part in first_error.get("loc", []))
    return _error_response(
        request,
        422,
        "VALIDATION_ERROR",
        f"{loc}: {msg}" if loc else msg,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return _error_response(
        request,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "INTERNAL_SERVER_ERROR",
        "Terjadi kesalahan internal pada server AmbatuFit.",
    )


@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "service": "ambatufit-core",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


app.include_router(identity_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")
app.include_router(medication_router, prefix="/api/v1")
app.include_router(knowledge_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(plan_router, prefix="/api/v1")
app.include_router(consultation_router, prefix="/api/v1")

# Mirror partner integration routes on core app (hidden from core OpenAPI contract) so mobile Wi-Fi clients
# work reliably even when port 8200 is unreachable or filtered on LAN.
from fastapi import APIRouter
from integration.server import get_fitness_gyms, get_nutrition_foods, get_status, authorize as integration_authorize
from fastapi import Depends

_integration_mirror = APIRouter(prefix="/integration/v1", include_in_schema=False)
_integration_mirror.add_api_route("/status", get_status, methods=["GET"], dependencies=[Depends(integration_authorize)])
_integration_mirror.add_api_route("/nutrition/foods", get_nutrition_foods, methods=["GET"], dependencies=[Depends(integration_authorize)])
_integration_mirror.add_api_route("/fitness/gyms", get_fitness_gyms, methods=["GET"], dependencies=[Depends(integration_authorize)])
app.include_router(_integration_mirror)
