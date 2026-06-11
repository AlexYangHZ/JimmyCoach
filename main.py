"""JimmyCoach — AI tutoring coach for Jimmy."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager

from config import settings
from db.database import init_db
from routes import pages, chat, exercises, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    app.state.templates = Jinja2Templates(directory="templates")
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/textbook", StaticFiles(directory="data/textbooks"), name="textbook")

app.include_router(pages.router)
app.include_router(chat.router)
app.include_router(exercises.router)
app.include_router(admin.router)


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.app_name}
