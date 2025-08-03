from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from prometheus_client import Counter, Histogram, generate_latest
from starlette.requests import Request
from starlette.responses import Response

from src.api.routes import practices_router, scraper_router
from src.core.config import settings
from src.core.logging import get_logger, setup_logging
from src.utils.metrics import (
    api_request_counter,
    api_request_duration,
    setup_metrics,
)

logger = get_logger(__name__)

# API Key authentication
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """Verify API key for authentication."""
    if api_key != settings.api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    setup_logging()
    setup_metrics()
    logger.info("Starting SOTA Practices API", version=app.version)
    
    yield
    
    # Shutdown
    logger.info("Shutting down SOTA Practices API")


app = FastAPI(
    title="SOTA Practices API",
    description="Queryable knowledge base for AI model best practices",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests and track metrics."""
    method = request.method
    path = request.url.path
    
    # Skip metrics endpoint
    if path == "/metrics":
        return await call_next(request)
    
    # Track metrics
    api_request_counter.labels(method=method, endpoint=path).inc()
    
    with api_request_duration.labels(method=method, endpoint=path).time():
        response = await call_next(request)
    
    logger.info(
        "API request",
        method=method,
        path=path,
        status_code=response.status_code,
    )
    
    return response


@app.get("/", response_class=JSONResponse)
async def root():
    """Root endpoint with API information."""
    return {
        "service": "SOTA Practices API",
        "version": "0.1.0",
        "description": "Queryable knowledge base for AI model best practices",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "metrics": "/metrics",
            "api": {
                "models": f"{settings.api_prefix}/models",
                "scrapers": f"{settings.api_prefix}/scrapers",
            },
        },
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "sota-practices-api",
        "version": "0.1.0",
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type="text/plain")


# Include routers
app.include_router(
    practices_router,
    prefix=f"{settings.api_prefix}/models",
    tags=["models"],
    dependencies=[Security(verify_api_key)],
)

app.include_router(
    scraper_router,
    prefix=f"{settings.api_prefix}/scrapers",
    tags=["scrapers"],
    dependencies=[Security(verify_api_key)],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with structured response."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "path": str(request.url.path),
            }
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(
        "Unhandled exception",
        error=str(exc),
        path=str(request.url.path),
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": 500,
                "message": "Internal server error",
                "path": str(request.url.path),
            }
        },
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.api.server:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_config=None,  # Use our custom logging
    )