"""Cliente HTTP para a API Eletrofrio.

Centraliza o consumo dos 4 endpoints do hackathon. Usa httpx async para
ficar compatível com FastAPI.

Decisão: `verify=False` porque o host usa porta não-padrão e certificado
que às vezes falha em ambientes de teste. Em produção: remover.
"""
from typing import Any, Optional
import httpx
from loguru import logger

from src.config import settings


class EletrofrioClient:
    def __init__(self, base_url: Optional[str] = None, timeout: float = 30.0):
        self.base_url = base_url or settings.eletrofrio_api_url
        self._client = httpx.AsyncClient(timeout=timeout, verify=False)

    async def close(self) -> None:
        await self._client.aclose()

    async def _get(self, params: dict[str, Any]) -> Any:
        logger.debug(f"GET {self.base_url} params={params}")
        r = await self._client.get(self.base_url, params=params)
        r.raise_for_status()
        return r.json()

    async def fetch_alarms(self) -> list[dict[str, Any]]:
        data = await self._get({"route": "alarmes"})
        return data if isinstance(data, list) else data.get("data", [])

    async def fetch_units(self) -> list[dict[str, Any]]:
        data = await self._get({"route": "unidades"})
        return data if isinstance(data, list) else data.get("data", [])

    async def fetch_telemetry(self, device_id: int) -> dict[str, Any]:
        """Telemetria vem no formato Chart.js: {labels, datasets:[{label,color,values}]}.

        Mantemos o formato bruto (já consumível pelo front) e deixamos a
        extração de temperaturas para o TelemetryAgent.
        """
        data = await self._get({"route": "telemetria", "dispositivoId": device_id})
        if isinstance(data, dict):
            return data
        # Fallback: API um dia retornou lista — embrulha no formato novo
        return {"labels": [], "datasets": [], "_legacy": data}
