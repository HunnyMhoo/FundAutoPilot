"""Switch Impact Simulator API - Main Application."""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.api.funds import router as funds_router
from app.api.switch import router as switch_router
from app.core.database import get_db, sync_engine, Base
from app.services.fund_service import FundService
from app.models.fund import MetaResponse
from fastapi import HTTPException

# Import all ORM models to ensure they're registered with Base.metadata
from app.models import fund_orm  # noqa: F401 - Import needed for table creation

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Switch Impact Simulator API",
    description="API for mutual fund comparison and switch impact simulation",
    version="0.1.0",
)


@app.on_event("startup")
async def startup_event():
    """Create database tables if they don't exist on startup."""
    try:
        logger.info("Creating database tables if they don't exist...")
        Base.metadata.create_all(sync_engine)
        logger.info("Database tables ready.")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}", exc_info=True)
        # Don't raise - allow server to start even if tables exist

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(funds_router)
app.include_router(switch_router)


@app.get("/")
def read_root():
    """Root endpoint with API info."""
    return {
        "message": "Welcome to Switch Impact Simulator API",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/meta", response_model=MetaResponse)
async def get_meta(
    db: AsyncSession = Depends(get_db),
) -> MetaResponse:
    """
    Get metadata for home page (fund count and data freshness).
    
    Returns cached metadata with 5-minute TTL to ensure fast response times.
    """
    # #region agent log
    import json; log_data = {"location": "main.py:53", "message": "get_meta entry (main)", "data": {"has_db": db is not None}, "timestamp": __import__("time").time(), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "A"}; open("/Users/test/AutoInvest/FundAutoPilot/.cursor/debug.log", "a").write(json.dumps(log_data) + "\n")
    # #endregion
    try:
        service = FundService(db)
        # #region agent log
        log_data = {"location": "main.py:64", "message": "Before service.get_meta_stats call (main)", "data": {}, "timestamp": __import__("time").time(), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "B"}; open("/Users/test/AutoInvest/FundAutoPilot/.cursor/debug.log", "a").write(json.dumps(log_data) + "\n")
        # #endregion
        stats = await service.get_meta_stats()
        # #region agent log
        log_data = {"location": "main.py:65", "message": "After service.get_meta_stats call (main)", "data": {"stats_keys": list(stats.keys()) if isinstance(stats, dict) else "not_dict"}, "timestamp": __import__("time").time(), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "B"}; open("/Users/test/AutoInvest/FundAutoPilot/.cursor/debug.log", "a").write(json.dumps(log_data) + "\n")
        # #endregion
        return MetaResponse(**stats)
    except Exception as e:
        # #region agent log
        log_data = {"location": "main.py:67", "message": "Exception in get_meta (main)", "data": {"error_type": type(e).__name__, "error_msg": str(e)}, "timestamp": __import__("time").time(), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "B"}; open("/Users/test/AutoInvest/FundAutoPilot/.cursor/debug.log", "a").write(json.dumps(log_data) + "\n")
        # #endregion
        raise HTTPException(status_code=500, detail=f"Failed to fetch metadata: {str(e)}")
