import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

load_dotenv()

from app.core.config import settings
from app.api.health import router as health_router
from app.api.projects import router as projects_router
from app.api.jobs import router as jobs_router
from app.api.explain import router as explain_router
from app.api.tests import router as tests_router
from app.api.coverage import router as coverage_router
from app.api.refactor import router as refactor_router

app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered developer tool for legacy code analysis, test generation, and refactoring.",
    version=settings.VERSION,
)

# CORS middleware configuration with robust wildcard & credentials support
cors_origins = [o for o in settings.ALLOWED_ORIGINS if o != "*"]
cors_regex = r"^https?://.*$" if "*" in settings.ALLOWED_ORIGINS else None

if cors_regex:
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=cors_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include routes under /api
app.include_router(health_router, prefix=settings.API_V1_STR)
app.include_router(projects_router, prefix=settings.API_V1_STR)
app.include_router(jobs_router, prefix=settings.API_V1_STR)
app.include_router(explain_router, prefix=settings.API_V1_STR)
app.include_router(tests_router, prefix=settings.API_V1_STR)
app.include_router(coverage_router, prefix=settings.API_V1_STR)
app.include_router(refactor_router, prefix=settings.API_V1_STR)

# Root health check endpoint
app.include_router(health_router, prefix="")

# Optional Static SPA frontend mounting for unified container deployments
candidate_frontend_paths = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")),
    os.path.abspath(os.path.join(os.getcwd(), "frontend", "dist")),
    os.path.abspath(os.path.join(os.getcwd(), "..", "frontend", "dist")),
    "/app/frontend/dist",
]

frontend_dist = next(
    (p for p in candidate_frontend_paths if os.path.isdir(p) and os.path.exists(os.path.join(p, "index.html"))),
    None
)

if frontend_dist:
    assets_dir = os.path.join(frontend_dist, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="static-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        # Don't intercept API or docs routes
        if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("openapi.json") or full_path.startswith("redoc") or full_path == "health":
            return None
        # Check if the requested file exists directly inside dist (e.g. favicon.ico, vite.svg)
        candidate_file = os.path.join(frontend_dist, full_path)
        if full_path and os.path.isfile(candidate_file):
            return FileResponse(candidate_file)
        # Fallback to index.html for SPA client-side routing
        return FileResponse(os.path.join(frontend_dist, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=True)
