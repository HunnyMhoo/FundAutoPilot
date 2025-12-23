"""Switch Impact Simulator API - Main Application."""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.funds import router as funds_router
from app.core.database import get_db
from app.services.fund_service import FundService
from app.models.fund import MetaResponse
from fastapi import HTTPException

app = FastAPI(
    title="Switch Impact Simulator API",
    description="API for mutual fund comparison and switch impact simulation",
    version="0.1.0",
)

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
    try:
        service = FundService(db)
        stats = await service.get_meta_stats()
        return MetaResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch metadata: {str(e)}")
