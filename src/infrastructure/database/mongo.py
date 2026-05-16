"""Repositório MongoDB (motor - async).

Persistência é **best-effort**: se o Mongo estiver indisponível (ex.: cluster
Atlas pausado), as gravações apenas logam e seguem — a análise, o gráfico e o
RAG continuam funcionando. O único efeito é não registrar histórico.

Coleções:
- telemetry_history
- alarm_history
- agent_decisions
- tickets
"""
from datetime import datetime
from typing import Any
from motor.motor_asyncio import AsyncIOMotorClient
from loguru import logger

from src.config import settings


class MongoRepository:
    def __init__(self, uri: str | None = None, db_name: str | None = None):
        # serverSelectionTimeoutMS curto: se o Atlas estiver fora, falha em ~3s
        # em vez de travar a request por 30s (default).
        self.client = AsyncIOMotorClient(
            uri or settings.mongo_uri,
            serverSelectionTimeoutMS=3000,
            connectTimeoutMS=3000,
        )
        self.db = self.client[db_name or settings.mongo_db]

    async def save_telemetry(self, device_id: int, data: Any) -> None:
        if not data:
            return
        doc = {"device_id": device_id, "data": data, "collected_at": datetime.utcnow()}
        await self._safe_insert("telemetry_history", doc)

    async def save_alarms(self, alarms: list[dict[str, Any]]) -> None:
        if not alarms:
            return
        doc = {"alarms": alarms, "collected_at": datetime.utcnow()}
        await self._safe_insert("alarm_history", doc)

    async def save_decision(self, decision: dict[str, Any]) -> None:
        await self._safe_insert("agent_decisions", decision)

    async def save_ticket(self, ticket: dict[str, Any]) -> None:
        ticket = {**ticket, "created_at": datetime.utcnow()}
        await self._safe_insert("tickets", ticket)

    async def recent_decisions(self, limit: int = 500) -> list[dict[str, Any]]:
        """Decisões mais recentes (usado para enriquecer a tela inicial).

        Best-effort: se o Mongo estiver fora, retorna lista vazia e a UI
        apenas mostra os devices sem a última severidade.
        """
        try:
            cursor = self.db.agent_decisions.find().sort("created_at", -1).limit(limit)
            return [doc async for doc in cursor]
        except Exception as e:
            logger.warning(f"[Mongo] recent_decisions indisponível — seguindo sem: {e}")
            return []

    async def _safe_insert(self, collection: str, doc: dict[str, Any]) -> None:
        try:
            await self.db[collection].insert_one(doc)
        except Exception as e:
            logger.warning(
                f"[Mongo] Falha ao gravar em '{collection}' — "
                f"persistência ignorada (app segue): {e}"
            )

    async def ping(self) -> bool:
        try:
            await self.client.admin.command("ping")
            return True
        except Exception as e:
            logger.error(f"Mongo ping fail: {e}")
            return False

    def close(self) -> None:
        self.client.close()
