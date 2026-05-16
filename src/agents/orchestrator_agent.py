"""Orchestrator Agent - roteador central de tarefas entre agentes.

Responsabilidade única: classificar a severidade do estado do dispositivo e
delegar cada subtarefa ao agente adequado. NÃO executa parsing, não monta
payloads, não fala com APIs externas — apenas decide quem faz o quê.

Pipeline determinístico (regras antes de qualquer LLM):
- TelemetryAgent  → estatísticas de temperatura
- AlarmAgent      → contagem/padrões de alarmes
- _classify       → severity ∈ {ok, warning, critical}
- RagAgent        → recomendação técnica (warning/critical)
- TicketAgent     → abertura de chamado (critical)
"""
from typing import Any

from loguru import logger

from src.config import settings
from src.domain.entities import AgentDecision
from src.agents.alarm_agent import AlarmAgent
from src.agents.rag_agent import RagAgent
from src.agents.telemetry_agent import TelemetryAgent
from src.agents.ticket_agent import TicketAgent


class OrchestratorAgent:
    def __init__(
        self,
        telemetry_agent: TelemetryAgent,
        alarm_agent: AlarmAgent,
        rag_agent: RagAgent,
        ticket_agent: TicketAgent,
    ):
        self.telemetry = telemetry_agent
        self.alarms = alarm_agent
        self.rag = rag_agent
        self.tickets = ticket_agent

    # --- Classificação (única regra de negócio que fica aqui) -----------

    def _classify(self, telemetry_stats: dict, alarm_stats: dict) -> tuple[str, str]:
        """Retorna (severity, reason)."""
        if alarm_stats["critical_repeats"]:
            return "critical", (
                f"Alarmes repetidos ({alarm_stats['max_repeats']}x) — "
                "padrão crítico detectado."
            )
        if telemetry_stats["high_temp_alert"]:
            return "warning", (
                f"Temperatura máxima {telemetry_stats['max_temp']:.1f}°C "
                f"acima do limite {settings.temperature_threshold}°C."
            )
        if alarm_stats["device_alarms_count"] > 0:
            return "warning", (
                f"Dispositivo possui {alarm_stats['device_alarms_count']} alarme(s) recente(s)."
            )
        if telemetry_stats["max_temp"] is None:
            return "warning", "Dados inconsistentes / telemetria ausente — consultar RAG."
        return "ok", "Temperatura e alarmes dentro da normalidade."

    # --- Fluxo principal: roteamento entre agentes ----------------------

    async def analyze(
        self,
        device_id: int,
        telemetry: Any,
        alarms: list[dict[str, Any]],
        unit_info: dict[str, Any] | None = None,
    ) -> AgentDecision:
        # 1) Delega análise de dados aos agentes especializados
        tel_stats = self.telemetry.analyze(telemetry)
        alm_stats = self.alarms.analyze(alarms, device_id)

        # 2) Decide severidade (única responsabilidade própria)
        severity, reason = self._classify(tel_stats, alm_stats)
        logger.info(f"[Orchestrator] device={device_id} severity={severity} — {reason}")

        decision = AgentDecision(
            device_id=device_id,
            severity=severity,
            action="direct_response",
            reason=reason,
        )

        if severity == "ok":
            logger.info("[Orchestrator] Resposta direta — sem RAG, sem chamado")
            return decision

        # 3) Delega busca de conhecimento ao RAG
        logger.info("[Orchestrator] Delegando ao RAG Agent")
        query = (
            f"Dispositivo {device_id} — {reason}. "
            f"Telemetria: max={tel_stats['max_temp']}, "
            f"alarmes recentes={alm_stats['device_alarms_count']}."
        )
        rag_text = await self.rag.diagnose(query)
        decision.rag_recommendation = rag_text
        decision.action = "rag_lookup"

        if severity != "critical":
            return decision

        # 4) Delega abertura de chamado ao TicketAgent
        logger.warning("[Orchestrator] Delegando ao Ticket Agent — anomalia crítica")
        success, resp = await self.tickets.open(
            device_id=device_id,
            alarm_stats=alm_stats,
            reason=reason,
            rag_text=rag_text,
            unit_info=unit_info,
        )
        decision.ticket_opened = success
        decision.ticket_response = resp
        if success:
            decision.action = "open_ticket"

        return decision
