"""
AgriNext Backend Entrypoint.
FastAPI Application serving NASA Earth Observation Data and
Climate-Resilient Crop Rotation Recommendations.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")
load_dotenv(Path(__file__).resolve().parent / ".env.local")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.router import router as core_router
import database

app = FastAPI(
    title="AgriNext – NASA-Powered Decision Support System",
    description="Climate-resilient crop rotation recommendations backed by real NASA Earth observation data.",
    version="1.0.0"
)

# Enable CORS for local Vite development
_allowed_origins = [
    origin.strip() for origin in os.getenv(
        "AGRINEXT_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
    ).split(",") if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)

app.include_router(core_router)

@app.on_event("startup")
def recover_interrupted_jobs():
    database.recover_interrupted_nasa_jobs()
    database.cleanup_old_nasa_jobs(retention_days=30)

@app.get("/")
def root():
    return {
        "message": "Welcome to AgriNext API",
        "docs_url": "/docs",
        "health_check": "/api/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
