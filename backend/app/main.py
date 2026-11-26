import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    global_exception_handler,
)

from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.transactions import router as transactions_router
from app.api.v1.reconciliation import router as reconciliation_router
from app.api.v1.quarantine import router as quarantine_router
from app.api.v1.live import router as live_router
from app.api.v1.pricing import router as pricing_router
from app.api.v1.ai import router as ai_router
from app.api.v1.auth import router as auth_router

app = FastAPI(
    title="Brightleaf Market — Retail Operations Platform",
    description="Next-generation enterprise retail operations platform integrating live monitoring, automated daily EOD reconciliation, two-way price synchronization, and multimodal AI intelligence.",
    version="1.0.0"
)

# Register Unified Simplified Exception Handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

# Enable CORS for local development and tablet browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
api_v1_prefix = "/api/v1"
app.include_router(dashboard_router, prefix=api_v1_prefix)
app.include_router(transactions_router, prefix=api_v1_prefix)
app.include_router(reconciliation_router, prefix=api_v1_prefix)
app.include_router(quarantine_router, prefix=api_v1_prefix)
app.include_router(live_router, prefix=api_v1_prefix)
app.include_router(pricing_router, prefix=api_v1_prefix)
app.include_router(ai_router, prefix=api_v1_prefix)
app.include_router(auth_router, prefix=api_v1_prefix)


@app.get("/api/health")
async def health_check():
    return {
        "status": "HEALTHY",
        "service": "Brightleaf Retail Operations Platform",
        "version": "1.0.0"
    }


# Static files and SPA dashboard route
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
@app.get("/dashboard")
async def serve_dashboard():
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return JSONResponse(
        content={"message": "Brightleaf Retail Operations API Online. Dashboard UI loading..."},
        status_code=200
    )
