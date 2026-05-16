"""Entrypoint da aplicação FastAPI."""
import os

import uvicorn

from src.interfaces.api.app import create_app

app = create_app()

if __name__ == "__main__":
    # Render (e a maioria dos PaaS) injeta a porta via $PORT.
    # reload só em dev local: defina DEV_RELOAD=1 no .env.
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("DEV_RELOAD", "").strip() in {"1", "true", "True"}
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=reload)
