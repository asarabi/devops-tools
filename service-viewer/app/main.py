import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from .api.services import router as services_router

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Service Viewer",
    description="Dedicated lightweight dashboard for custom user-managed systemd services",
    version="1.0.0",
)

# Static & Templates
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# API Routes
app.include_router(services_router)


@app.get("/")
def index(request: Request):
    is_root = os.geteuid() == 0
    return templates.TemplateResponse("index.html", {"request": request, "is_root": is_root})


@app.get("/health")
def health():
    return {"status": "ok", "app": "service-viewer"}
