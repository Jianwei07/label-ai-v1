import logging
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Correctly import from your project structure
from app.core.config import settings
from app.api.v1.labels import router as labels_router
from app.api.v1.rules import router as rules_router
from app.utils.custom_exceptions import CoreServiceError
from app.db.session import database, engine # <-- ADDED: Import engine
from app.models.analysis_result import metadata as analysis_metadata # <-- ADDED: Import metadata

# Configure logging using settings from config.py
logging.basicConfig(level=settings.LOG_LEVEL.upper())
logger = logging.getLogger(settings.APP_NAME)

# --- Define Startup and Shutdown Events as Functions ---
async def startup_event():
    """Connect to database and create tables on startup."""
    try:
        # Create the database table if it doesn't exist.
        analysis_metadata.create_all(bind=engine)
        await database.connect()
        logger.info("Database connection established and tables created.")
    except Exception as e:
        logger.critical(f"Could not connect to database or create tables: {e}", exc_info=True)

async def shutdown_event():
    """Disconnect from database on shutdown."""
    try:
        await database.disconnect()
        logger.info("Database connection closed.")
    except Exception as e:
        logger.error(f"Error disconnecting from database: {e}", exc_info=True)


# --- UPDATED: FastAPI app with event handlers as functions ---
app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="API for checking regulatory compliance of product labels.",
    on_startup=[startup_event],  # Use the function here
    on_shutdown=[shutdown_event], # Use the function here
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
