from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv
import os
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

# Setup logging first
from app.utils.logging_config import setup_logging
setup_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    log_file=os.getenv("LOG_FILE", "logs/app.log")
)

from app.utils.database import engine, Base
from app.routers import auth, applications, admin, analytics, scraper, ai_features, resume, job_matching, jobs
from app.api import notifications
from app.middleware import RequestTrackingMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.utils.exceptions import JobTrackerException
from app.utils.exception_handlers import (
    job_tracker_exception_handler,
    validation_exception_handler,
    database_exception_handler,
    generic_exception_handler
)
from app.utils.rate_limiter import limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Job Tracker API",
    description="""
## Intelligent Job Application Tracking System

**Authentication Required** - Most endpoints require Bearer token authentication.

### Quick Start:
1. Login via `/api/auth/login` endpoint
2. Copy the `access_token` from response
3. Click **Authorize** button ([LOCK] top right)
4. Paste token and click **Authorize**

Admin endpoints require admin role.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add rate limiting state
app.state.limiter = limiter

# Add custom middleware
app.add_middleware(RequestTrackingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"]
)

# Include routers
app.include_router(auth.router)
app.include_router(applications.router)
app.include_router(admin.router)
app.include_router(analytics.router)
app.include_router(scraper.router)
app.include_router(ai_features.router)
app.include_router(resume.router)
app.include_router(job_matching.router)
app.include_router(jobs.router)
app.include_router(notifications.router)

# Exception handlers
app.add_exception_handler(JobTrackerException, job_tracker_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, database_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Mount static files (frontend)
frontend_path = Path(__file__).parent.parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/frontend", StaticFiles(directory=str(frontend_path)), name="frontend")
    print("[OK] Frontend files mounted at:", frontend_path)

@app.on_event("startup")
def startup():
    import logging
    logger = logging.getLogger("main")
    logger.info("Starting JobSphere API...")
    logger.info("Configuration validated: ok")
    logger.info("Environment: development" if os.getenv("DEBUG") else "Environment: production")
    logger.info("Configuration info:")
    logger.info(f"  app_name: {os.getenv('APP_NAME', 'JobSphere')}")
    logger.info(f"  app_version: {os.getenv('APP_VERSION', '1.0.0')}")
    logger.info(f"  environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"  debug: {os.getenv('DEBUG', 'True')}")
    logger.info(f"  database: SQLite")
    logger.info(f"  rate_limit: 100 req/min")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        reload=False
    )
