import logging
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Correctly import from your project structure
from app.core.config import settings
from app.api.v1.labels import router as labels_router # Corrected import
from app.api.v1.rules import router as rules_router # Corrected import
from app.utils.custom_exceptions import CoreServiceError

# Configure logging using settings from config.py
logging.basicConfig(level=settings.LOG_LEVEL.upper())
logger = logging.getLogger(settings.APP_NAME)

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="API for checking regulatory compliance of product labels.",
    # The interactive docs will be available at /docs and /redoc by default
)

# --- Middleware ---
# Configure CORS to allow your frontend to communicate with this backend
app.add_middleware(
    CORSMiddleware,
    # In production, you should restrict this to your actual frontend domain
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Exception Handlers ---
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handles errors from Pydantic model validation."""
    logger.error(f"Request validation error: {exc.errors()}", exc_info=False)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "message": "Validation Error"},
    )

@app.exception_handler(CoreServiceError)
async def core_service_exception_handler(request: Request, exc: CoreServiceError):
    """Handles custom application-specific errors from the service layer."""
    logger.error(f"Core service error: {exc.message}", exc_info=True)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message, "error_code": exc.error_code},
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Catches any other unhandled errors to prevent server crashes."""
    logger.critical(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred on the server."},
    )


# --- Routers ---
# Include the routers from your endpoint files.
# This makes your API modular. All routes from labels.py will be under /api/v1/labels
# and all from rules.py will be under /api/v1/rules
app.include_router(labels_router, prefix=f"{settings.API_V1_STR}/labels", tags=["Labels"])
app.include_router(rules_router, prefix=f"{settings.API_V1_STR}/rules", tags=["Rules"])


# --- Root and Health Check Endpoints ---
@app.get("/", tags=["Root"])
async def read_root():
    """Root endpoint providing basic application information."""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": app.version,
        "docs_url": app.docs_url,
        "redoc_url": app.redoc_url
    }

@app.get("/health", tags=["Health"], status_code=status.HTTP_200_OK)
async def health_check():
    """Simple health check endpoint for monitoring."""
    return {"status": "healthy"}

