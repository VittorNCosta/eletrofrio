"""Entidades de domínio - representam conceitos do negócio.

Modelo leve: só o necessário para o fluxo de análise + alerta ao cliente.
"""
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class Alarm(BaseModel):
    dispositivo_id: Optional[int] = None
    loja_id: Optional[int] = None
    loja_nome: Optional[str] = None
    tag: Optional[str] = None
    descricao: Optional[str] = None
    data: Optional[str] = None
    raw: dict[str, Any] = Field(default_factory=dict)


class Unit(BaseModel):
    loja_id: int
    loja_nome: str
    raw: dict[str, Any] = Field(default_factory=dict)


class TelemetryReading(BaseModel):
    dispositivo_id: int
    temperatura: Optional[float] = None
    timestamp: Optional[str] = None
    raw: dict[str, Any] = Field(default_factory=dict)


class AgentDecision(BaseModel):
    """Decisão tomada pelo Orchestrator Agent."""
    device_id: int
    severity: str  # "ok" | "warning" | "critical"
    action: str    # "direct_response" | "rag_lookup"
    reason: str
    rag_recommendation: Optional[str] = None
    notification_sent: bool = False
    notification_response: Optional[dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
