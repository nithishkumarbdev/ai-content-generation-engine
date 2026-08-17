import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db
from app.routers import health, jobs
from app.utils.files import ensure_dirs

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="GlitrAI Mini Content Engine",
    description="Turns a product name, description, and reference image into a generated creative.",
    version="1.0.0",
    lifespan=lifespan,
)

# Kept permissive since the frontend may be hosted on a different origin
# than the API (e.g. static hosting vs. API host). Tighten to specific
# origins if you deploy frontend and backend separately.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Must happen before the StaticFiles mount below - it requires the
# directory to exist already, and that check runs at import time, not
# when the server actually starts handling requests.
ensure_dirs()
app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")

app.include_router(health.router)
app.include_router(jobs.router)

# Serves frontend/index.html at "/" so the whole app (API + UI) is a single
# deployable unit. If you'd rather host the frontend separately (e.g. on
# Vercel/Netlify), this mount can simply be removed.
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
