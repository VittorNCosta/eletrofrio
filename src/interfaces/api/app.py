"""Factory FastAPI."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from loguru import logger

from src.interfaces.api.routes import router
from src.interfaces.api.dependencies import get_api_client, get_mongo, get_rag_agent

WEB_STATIC_DIR = Path(__file__).resolve().parents[1] / "web" / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Boot: inicializando clientes")
    get_api_client()
    get_mongo()
    get_rag_agent()
    yield
    logger.info("Shutdown: fechando conexões")
    await get_api_client().close()
    get_mongo().close()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Eletrofrio AI Backend",
        description="Sistema inteligente de suporte à manutenção de refrigeração comercial.",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.include_router(router, prefix="/api")
    app.mount("/", StaticFiles(directory=str(WEB_STATIC_DIR), html=True), name="web")
    return app
