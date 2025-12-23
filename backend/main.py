"""Switch Impact Simulator API - Main Application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.funds import router as funds_router

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
