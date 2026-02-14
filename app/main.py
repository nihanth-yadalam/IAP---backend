"""
IAP Merged Backend — FastAPI application entry point.
Merges System A (Intelligent Academic Planner) + System B (Calendar Sync).
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.router import api_router
from app.background.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# CORS — allow all for dev; tighten for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the merged API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": settings.PROJECT_NAME}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
    )
