"""JimmyCoach — AI tutoring coach for Jimmy."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from config import settings

app = FastAPI(title=settings.app_name)


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.app_name}
