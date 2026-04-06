import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.models import init_db, get_db, Source
from app.api.routes import router as api_router
from app.sync.scheduler import start_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs("data", exist_ok=True)
    init_db()
    config_path = os.environ.get("CONFIG_PATH", "/app/config.yaml")
    if os.path.exists(config_path):
        try:
            start_scheduler()
        except Exception as e:
            logging.getLogger(__name__).warning(f"Scheduler not started: {e}")
    yield


app = FastAPI(title="Gerrit Manager", lifespan=lifespan)
app.include_router(api_router)

templates_dir = os.path.join(os.path.dirname(__file__), "templates")
static_dir = os.path.join(os.path.dirname(__file__), "static")
templates = Jinja2Templates(directory=templates_dir)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def dashboard(request: Request, db: Session = Depends(get_db)):
    sources = db.query(Source).all()
    return templates.TemplateResponse("index.html", {"request": request, "sources": sources})
