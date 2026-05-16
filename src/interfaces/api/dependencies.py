"""Wiring de dependências (injeção via FastAPI).

Mantém instâncias singleton de: Mongo, API client, agentes e Orchestrator.
"""
from functools import lru_cache

from src.agents.alarm_agent import AlarmAgent
from src.agents.orchestrator_agent import OrchestratorAgent
from src.agents.rag_agent import RagAgent
from src.agents.telemetry_agent import TelemetryAgent
from src.agents.ticket_agent import TicketAgent
from src.application.analyze_device import AnalyzeDeviceUseCase
from src.infrastructure.database.mongo import MongoRepository
from src.infrastructure.external_api.eletrofrio_client import EletrofrioClient


@lru_cache
def get_mongo() -> MongoRepository:
    return MongoRepository()


@lru_cache
def get_api_client() -> EletrofrioClient:
    return EletrofrioClient()


@lru_cache
def get_rag_agent() -> RagAgent:
    return RagAgent()


@lru_cache
def get_telemetry_agent() -> TelemetryAgent:
    return TelemetryAgent()


@lru_cache
def get_alarm_agent() -> AlarmAgent:
    return AlarmAgent()


@lru_cache
def get_ticket_agent() -> TicketAgent:
    return TicketAgent(api_client=get_api_client())


@lru_cache
def get_orchestrator() -> OrchestratorAgent:
    return OrchestratorAgent(
        telemetry_agent=get_telemetry_agent(),
        alarm_agent=get_alarm_agent(),
        rag_agent=get_rag_agent(),
        ticket_agent=get_ticket_agent(),
    )


def get_analyze_use_case() -> AnalyzeDeviceUseCase:
    return AnalyzeDeviceUseCase(
        api=get_api_client(),
        mongo=get_mongo(),
        orchestrator=get_orchestrator(),
    )
