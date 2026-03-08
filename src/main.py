"""App FastAPI e entrypoints."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.routes import router
from src.kafka.producer import get_producer, stop_producer


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await stop_producer()


app = FastAPI(
    title="AI YouTube Music Publisher",
    description="API para gerar músicas (Suno), montar vídeos e publicar no YouTube.",
    lifespan=lifespan,
)
app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}
