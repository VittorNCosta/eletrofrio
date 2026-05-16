"""Use case: Analisar um dispositivo (fluxo principal).

Passos:
1. Buscar telemetria (API externa)
2. Buscar alarmes (API externa)
3. Buscar unidades para enriquecer contexto da loja
4. Salvar no MongoDB
5. Delegar ao Orchestrator Agent
6. Persistir decisão (e ticket, se houver)
"""
from typing import Any
from loguru import logger

from src.agents.orchestrator_agent import OrchestratorAgent
from src.infrastructure.database.mongo import MongoRepository
from src.infrastructure.external_api.eletrofrio_client import EletrofrioClient


class AnalyzeDeviceUseCase:
    def __init__(
        self,
        api: EletrofrioClient,
        mongo: MongoRepository,
        orchestrator: OrchestratorAgent,
    ):
        self.api = api
        self.mongo = mongo
        self.orchestrator = orchestrator

    async def execute(self, device_id: int) -> dict[str, Any]:
        logger.info(f"[UseCase] Iniciando análise device_id={device_id}")

        telemetry = await self.api.fetch_telemetry(device_id)
        alarms = await self.api.fetch_alarms()

        unit_info = await self._find_unit_for_device(device_id, alarms)

        # Persistência histórica
        await self.mongo.save_telemetry(device_id, telemetry)
        await self.mongo.save_alarms(alarms)

        decision = await self.orchestrator.analyze(
            device_id=device_id,
            telemetry=telemetry,
            alarms=alarms,
            unit_info=unit_info,
        )

        await self.mongo.save_decision(decision.model_dump())
        if decision.ticket_opened and decision.ticket_response:
            await self.mongo.save_ticket(
                {"device_id": device_id, "response": decision.ticket_response}
            )

        return decision.model_dump()

    async def _find_unit_for_device(
        self, device_id: int, alarms: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        """Tenta inferir a loja olhando os alarmes do próprio device."""
        for a in alarms:
            dev = a.get("dispositivoId") or a.get("dispositivo_id")
            if dev == device_id:
                return {
                    "lojaId": a.get("lojaId") or a.get("loja_id"),
                    "lojaNome": a.get("lojaNm") or a.get("lojaNome") or a.get("loja_nome"),
                }
        return None
