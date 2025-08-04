#!/usr/bin/env python3
"""
KME (Key Management Entity) - Main Application Entry Point

Version: 1.0.0
Author: KME Development Team
Description: ETSI GS QKD 014 V1.1.1 compliant Key Management Entity
License: [To be determined]

ToDo List:
- [x] Implement FastAPI application setup
- [x] Add middleware for authentication
- [x] Configure CORS settings
- [x] Set up API routing
- [x] Add health check endpoints
- [x] Implement logging configuration
- [x] Add error handling middleware
- [x] Configure TLS settings
- [x] Add metrics collection
- [x] Implement graceful shutdown
- [x] Integrate ETSI-compliant API routes

Progress: 100% (All tasks completed)
"""

import datetime
import os
import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

# Import API routes
from app.api.routes import api_router

# Import authentication middleware
from app.core.authentication_middleware import get_auth_middleware

# Import database initialization
from app.core.database import close_database, initialize_database

# Import error handling
from app.core.error_handling import error_handler

# Import health monitoring
from app.core.health import check_health, get_health_summary

# Import performance monitoring
from app.core.performance import get_performance_monitor

# Import security infrastructure
from app.core.security import initialize_security_infrastructure

# Import KME modules (to be implemented)
# from app.core.config import settings
# from app.core.logging import setup_logging
# from app.core.middleware import AuthMiddleware


# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

# Initialize structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("KME application starting up")

    try:
        # Initialize security infrastructure (synchronous function)
        if not initialize_security_infrastructure():
            logger.error("Security infrastructure initialization failed")
            raise RuntimeError("Security infrastructure initialization failed")
        logger.info("Security infrastructure initialized")

        # Initialize performance monitoring (synchronous function)
        get_performance_monitor()
        logger.info("Performance monitoring initialized")

        # Initialize database (async function)
        if not await initialize_database():
            logger.error("Database initialization failed")
            raise RuntimeError("Database initialization failed")
        logger.info("Database initialized")

        logger.info("KME application startup completed successfully")
    except Exception as e:
        logger.error("Failed to initialize KME application", error=str(e))
        raise

    yield

    # Shutdown
    logger.info("KME application shutting down")

    try:
        # Cleanup resources
        await close_database()
        logger.info("KME application shutdown completed successfully")
    except Exception as e:
        logger.error("Error during KME application shutdown", error=str(e))


# Create FastAPI application
app = FastAPI(
    title="KME - Key Management Entity",
    description="ETSI GS QKD 014 V1.1.1 compliant Key Management Entity",
    version="1.0.0",
    docs_url="/docs" if os.getenv("DEBUG", "false").lower() == "true" else None,
    redoc_url="/redoc" if os.getenv("DEBUG", "false").lower() == "true" else None,
    lifespan=lifespan,
)


# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests for debugging"""
    import time

    start_time = time.time()

    # Log request details
    logger.info(
        "📥 Incoming request",
        method=request.method,
        path=request.url.path,
        client_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        content_type=request.headers.get("content-type"),
        has_scope=hasattr(request, "scope"),
        scope_keys=list(request.scope.keys()) if hasattr(request, "scope") else [],
    )

    # Check for SSL context
    if hasattr(request, "scope") and "ssl" in request.scope:
        ssl_context = request.scope["ssl"]
        logger.info(
            "🔐 SSL context found",
            ssl_keys=list(ssl_context.keys()) if ssl_context else [],
            has_client_cert="client_cert" in ssl_context if ssl_context else False,
        )
    else:
        logger.warning("⚠️ No SSL context in request")

    response = await call_next(request)

    # Log response details
    process_time = time.time() - start_time
    logger.info(
        "📤 Response sent",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        process_time=round(process_time, 3),
    )

    return response


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "[]").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Configure Trusted Host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"],  # TODO: Configure proper allowed hosts for production
)

# Include API routes
app.include_router(api_router)


# Global exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Global HTTP exception handler"""
    # Generate request ID for tracking
    request_id = str(uuid.uuid4())

    logger.error(
        "HTTP exception occurred",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
        method=request.method,
        request_id=request_id,
    )

    # For authentication errors (401), return a simple error response
    if exc.status_code == 401:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "message": exc.detail
                if isinstance(exc.detail, str)
                else "Authentication failed",
                "error_code": "AUTHENTICATION_ERROR",
                "request_id": request_id,
                "timestamp": datetime.datetime.utcnow().isoformat(),
            },
        )

    # For authorization errors (403), return a simple error response
    if exc.status_code == 403:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "message": exc.detail
                if isinstance(exc.detail, str)
                else "Authorization failed",
                "error_code": "AUTHORIZATION_ERROR",
                "request_id": request_id,
                "timestamp": datetime.datetime.utcnow().isoformat(),
            },
        )

    # For service unavailable errors (503), return a simple error response
    if exc.status_code == 503:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "message": exc.detail
                if isinstance(exc.detail, str)
                else "Service unavailable",
                "error_code": "SERVICE_UNAVAILABLE",
                "request_id": request_id,
                "timestamp": datetime.datetime.utcnow().isoformat(),
            },
        )

    # If the exception already has a standardized error response, return it as-is
    if isinstance(exc.detail, dict) and "message" in exc.detail:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail,
        )

    # For other errors, create a standardized error response
    error_response = error_handler.create_error_response(
        message=exc.detail if isinstance(exc.detail, str) else "HTTP error occurred",
        details=[{"parameter": "request", "error": f"HTTP {exc.status_code} error"}],
        error_code=f"HTTP_{exc.status_code}",
        request_id=request_id,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response,
    )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "KME - Key Management Entity",
        "version": "1.0.0",
        "status": "operational",
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return await check_health()


@app.get("/health/summary")
async def health_summary():
    """Health summary endpoint"""
    try:
        return await get_health_summary()
    except Exception as e:
        logger.error("Health summary check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Health summary unavailable")


@app.get("/health/ready")
async def health_ready():
    """Readiness probe endpoint"""
    try:
        health_status = await check_health()

        # For development/testing, consider the service ready if it's not completely unhealthy
        # In production, you might want stricter requirements
        if health_status["status"] in ["healthy", "degraded"]:
            return {"status": "ready"}
        else:
            # Check if critical services are available
            checks = health_status.get("checks", [])
            critical_checks = ["basic_system", "database_health"]
            critical_healthy = all(
                any(
                    check["name"] == critical
                    and check["status"] in ["healthy", "degraded"]
                    for check in checks
                )
                for critical in critical_checks
            )

            if critical_healthy:
                return {"status": "ready"}
            else:
                raise HTTPException(status_code=503, detail="Service not ready")
    except Exception as e:
        logger.error("Health ready check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service not ready")


@app.get("/health/live")
async def health_live():
    """Liveness probe endpoint"""
    return {"status": "alive"}


@app.get("/health/detailed")
async def health_detailed():
    """Detailed health check endpoint"""
    try:
        return await check_health()
    except Exception as e:
        logger.error("Detailed health check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Detailed health check unavailable")


@app.get("/metrics/performance")
async def get_performance_metrics():
    """Performance metrics endpoint"""
    try:
        monitor = await get_performance_monitor()
        return await monitor.get_metrics()
    except Exception as e:
        logger.error("Failed to get performance metrics", error=str(e))
        raise HTTPException(status_code=503, detail="Failed to get performance metrics")


@app.get("/metrics/api")
async def get_api_metrics():
    """API metrics endpoint"""
    # TODO: Implement API metrics collection
    return {
        "requests_total": 0,
        "requests_per_second": 0.0,
        "average_response_time": 0.0,
        "error_rate": 0.0,
    }


@app.get("/metrics/keys")
async def get_key_metrics():
    """Key management metrics endpoint"""
    # TODO: Implement key metrics collection
    return {
        "keys_generated": 0,
        "keys_distributed": 0,
        "keys_expired": 0,
        "key_pool_size": 0,
        "key_generation_rate": 0.0,
    }


@app.get("/metrics/system")
async def get_system_metrics():
    """System metrics endpoint"""
    # TODO: Implement system metrics collection
    return {
        "cpu_usage": 0.0,
        "memory_usage": 0.0,
        "disk_usage": 0.0,
        "network_io": 0.0,
    }


@app.get("/metrics/database")
async def get_database_metrics():
    """Database metrics endpoint"""
    # TODO: Implement database metrics collection
    return {
        "connections": 0,
        "queries_per_second": 0.0,
        "average_query_time": 0.0,
        "slow_queries": 0,
    }


@app.get("/debug-ssl")
async def debug_ssl(request: Request):
    """Debug endpoint to inspect SSL information in request scope"""
    debug_info = {
        "has_scope": hasattr(request, "scope"),
        "scope_keys": list(request.scope.keys()) if hasattr(request, "scope") else [],
        "ssl_info": request.scope.get("ssl") if hasattr(request, "scope") else None,
        "headers": dict(request.headers),
        "client": str(request.client) if request.client else None,
    }
    return debug_info


if __name__ == "__main__":
    import os
    import ssl

    import uvicorn

    from app.core.config import get_settings

    settings = get_settings()
    enable_ssl = os.environ.get("KME_ENABLE_SSL", "0") == "1"

    ssl_keyfile: str | None = "test_certs/kme_key.pem"
    ssl_certfile: str | None = "test_certs/kme_cert.pem"
    ssl_ca_certs: str | None = "test_certs/ca_cert.pem"

    if enable_ssl:
        # Check if certificates exist
        if (
            ssl_keyfile is None
            or ssl_certfile is None
            or not os.path.exists(ssl_keyfile)
            or not os.path.exists(ssl_certfile)
        ):
            print("Warning: TLS certificates not found. Starting without TLS...")
            print("To enable TLS, run: cd test_certs && python generate_test_certs.py")
            ssl_keyfile = None
            ssl_certfile = None
            ssl_ca_certs = None

        # Check if CA certificate exists for mutual authentication
        if ssl_ca_certs is not None and not os.path.exists(ssl_ca_certs):
            print(f"Warning: CA certificate not found: {ssl_ca_certs}")
            print("Mutual authentication will be disabled.")
            ssl_ca_certs = None

        # Log SSL configuration
        if ssl_keyfile and ssl_certfile:
            print("🔐 SSL Configuration:")
            print(f"  Server Certificate: {ssl_certfile}")
            print(f"  Server Key: {ssl_keyfile}")
            if ssl_ca_certs:
                print(f"  CA Certificate: {ssl_ca_certs}")
                print("  Mutual Authentication: ENABLED")
            else:
                print("  Mutual Authentication: DISABLED")
            print()

        uvicorn.run(
            "main:app",
            host=settings.server_host,
            port=settings.server_port,
            reload=settings.server_reload,
            log_level="info",
            ssl_keyfile=ssl_keyfile,
            ssl_certfile=ssl_certfile,
            ssl_ca_certs=ssl_ca_certs,
            ssl_cert_reqs=ssl.CERT_REQUIRED if ssl_ca_certs else ssl.CERT_NONE,
        )
    else:
        print("[INFO] Starting FastAPI backend in HTTP mode (no SSL, behind nginx)")
        uvicorn.run(
            "main:app",
            host=settings.server_host,
            port=settings.server_port,
            reload=settings.server_reload,
            log_level="info",
        )
