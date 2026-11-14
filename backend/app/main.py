import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.db import init_db
from app.routers import incidents, interviews, system, webhooks
from app.services.llm import LLMError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("retrace")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    s = get_settings()
    if not s.admin_access_key:
        log.warning("ADMIN_ACCESS_KEY is empty: the dashboard API is open. Set it before exposing this server.")
    if not s.groq_api_key:
        log.warning("GROQ_API_KEY is empty: AI features will return errors until it is set.")
    yield


app = FastAPI(title="Retrace", version="1.0.0", lifespan=lifespan)
settings = get_settings()
app.add_middleware(
    CORSMiddleware, allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_methods=["*"], allow_headers=["*"],
)


@app.exception_handler(LLMError)
async def llm_error_handler(_request: Request, exc: LLMError):
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def unhandled(_request: Request, exc: Exception):
    log.exception("unhandled error", exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Unexpected server error."})


for r in (system.router, incidents.router, interviews.public, interviews.admin, webhooks.router):
    app.include_router(r)

static = Path(settings.static_dir)
if (static / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=static / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "Not found.")
        candidate = (static / path).resolve()
        if path and candidate.is_file() and static.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(static / "index.html")
