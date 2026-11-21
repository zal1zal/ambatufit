import uuid
from datetime import datetime
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from app.config import settings
from app.db import init_db
from app.contexts.identity_access.api import router as identity_router
from app.contexts.personal_health_intelligence.api import router as health_router
from app.contexts.consultation_booking.api import router as consultation_router

app = FastAPI(
    title="AmbatuFit STB Microservice",
    description="Core backend service for AmbatuFit AI-assisted personal health platform. Deployed on STB.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Initialize DB tables on startup
@app.on_event("startup")
def on_startup():
    init_db()

# Request ID & Logging Middleware
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", f"req-{uuid.uuid4().hex[:12]}")
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Standardized Error Envelope Handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = getattr(request.state, "request_id", f"req-{uuid.uuid4().hex[:12]}")
    code = "HTTP_ERROR"
    if exc.status_code == 400:
        code = "BAD_REQUEST"
    elif exc.status_code == 401:
        code = "UNAUTHORIZED"
    elif exc.status_code == 403:
        code = "FORBIDDEN"
    elif exc.status_code == 404:
        code = "NOT_FOUND"
    elif exc.status_code == 409:
        code = "CONFLICT"
    elif exc.status_code == 422:
        code = "UNPROCESSABLE_ENTITY"

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": code,
                "message": exc.detail,
                "request_id": request_id,
            }
        },
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = getattr(request.state, "request_id", f"req-{uuid.uuid4().hex[:12]}")
    first_error = exc.errors()[0] if exc.errors() else {}
    msg = first_error.get("msg", "Format data masukan tidak valid.")
    loc = ".".join(str(l) for l in first_error.get("loc", []))
    if loc:
        msg = f"{loc}: {msg}"

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": msg,
                "request_id": request_id,
            }
        },
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", f"req-{uuid.uuid4().hex[:12]}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Terjadi kesalahan internal pada server AmbatuFit.",
                "request_id": request_id,
            }
        },
    )

# Gateway and Load-Balancer Health Route
@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "service": "ambatufit-core",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

# Include routers under /api/v1 prefix
app.include_router(identity_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")
app.include_router(consultation_router, prefix="/api/v1")

