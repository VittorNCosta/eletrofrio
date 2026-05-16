"""Ticket Agent - monta payload e abre chamado via API externa.

Responsabilidade única: traduzir uma decisão de severidade crítica em um
chamado válido para a API Eletrofrio, isolando o orchestrator do schema
de payload e do tratamento de falhas da chamada externa.
"""
from typing import Any

from loguru import logger

from src.config import settings
from src.infrastructure.external_api.eletrofrio_client import EletrofrioClient


class TicketAgent:
    def __init__(self, api_client: EletrofrioClient):
        self.api = api_client

    def build_payload(
        self,
        device_id: int,
        alarm_stats: dict,
        reason: str,
        rag_text: str,
        unit_info: dict[str, Any] | None,
    ) -> dict[str, Any]:
        first = alarm_stats["device_alarms"][0] if alarm_stats["device_alarms"] else {}
        loja_id = (unit_info or {}).get("lojaId") or first.get("lojaId") or first.get("loja_id") or 0
        loja_nome = (
            (unit_info or {}).get("lojaNome")
            or first.get("lojaNm")
            or first.get("lojaNome")
            or first.get("loja_nome")
            or "Desconhecida"
        )
        tag = first.get("dispositivoNm") or first.get("tag") or "N/A"
        motivo = f"{reason} | RAG: {rag_text[:200]}"
        return {
            "equipe": settings.team_name,
            "lojaId": int(loja_id) if loja_id else 0,
            "lojaNome": loja_nome,
            "dispositivoId": device_id,
            "tag": tag,
            "motivoIA": motivo,
            "requerTecnico": True,
        }

    async def open(
        self,
        device_id: int,
        alarm_stats: dict,
        reason: str,
        rag_text: str,
        unit_info: dict[str, Any] | None,
    ) -> tuple[bool, dict[str, Any]]:
        """Retorna (sucesso, resposta_ou_erro)."""
        payload = self.build_payload(
            device_id=device_id,
            alarm_stats=alarm_stats,
            reason=reason,
            rag_text=rag_text,
            unit_info=unit_info,
        )
        try:
            resp = await self.api.open_ticket(payload)
            logger.info(f"[TicketAgent] Chamado aberto: {resp}")
            return True, resp
        except Exception as e:
            logger.error(f"[TicketAgent] Falha ao abrir chamado: {e}")
            return False, {"error": str(e)}
