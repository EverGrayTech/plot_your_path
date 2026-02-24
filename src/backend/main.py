"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.routers import jobs

app = FastAPI(
    title="Plot Your Path API",
    description="Backend API for job capture and career tracking",
    version="0.1.0",
)

# CORS middleware to allow the frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", settings.next_public_api_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(jobs.router, prefix="/api")
