from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse
from app.api.routes import router
from app.core.db import create_db_and_tables
from app.core import config
from app.version import APP_NAME, APP_VERSION
from pathlib import Path
import sys


@asynccontextmanager
async def lifespan(_app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(title=APP_NAME, version=APP_VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(config.CORS_ORIGINS),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(router, prefix="/api")


def _mount_frontend() -> None:
    # Serve built Vite frontend if present (for standalone packaging).
    frozen = getattr(sys, "frozen", False)
    meipass = Path(getattr(sys, "_MEIPASS", "")) if frozen else None

    if frozen:
        candidate_dirs = []
        if meipass:
            candidate_dirs.append(meipass / "pbm_model_interface" / "dist")
        candidate_dirs.extend(
            [
                Path(sys.executable).parent / "pbm_model_interface" / "dist",
                Path(sys.executable).parent / "dist",
            ]
        )
    else:
        candidate_dirs = [
            Path.cwd() / "pbm_model_interface" / "dist",
            Path(__file__).resolve().parents[3] / "pbm_model_interface" / "dist",
            Path.cwd() / "dist",
        ]
    dist_dir = next((p for p in candidate_dirs if p.exists() and p.is_dir()), None)
    if not dist_dir:
        return

    # Vite build typically has `index.html` + `assets/`.
    assets_dir = dist_dir / "assets"
    if assets_dir.exists() and assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="frontend-assets")

    index_html = dist_dir / "index.html"
    if not index_html.exists():
        return

    @app.get("/", include_in_schema=False)
    async def frontend_index():
        return FileResponse(str(index_html))

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        # Serve actual built files if they exist (e.g. vite.svg), otherwise SPA fallback.
        candidate_file = dist_dir / full_path
        if candidate_file.exists() and candidate_file.is_file():
            return FileResponse(str(candidate_file))
        return FileResponse(str(index_html))


_mount_frontend()
