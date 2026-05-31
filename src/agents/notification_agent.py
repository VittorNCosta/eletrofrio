"""Notification Agent - alerta o cliente via WhatsApp em casos críticos.

Responsabilidade única: dado um telefone e o contexto da decisão, montar a
mensagem PT-BR e despachar pelo NotifierGateway.
"""
import os
import re
from typing import Any
from urllib.parse import quote

from loguru import logger

from src.config import settings
from src.infrastructure.notifications.notifier_gateway import NotifierGateway


class NotificationAgent:
    def __init__(self, notifier: NotifierGateway):
        self.notifier = notifier

    # --- URL pública ------------------------------------------------------

    @staticmethod
    def _base_url() -> str:
        """URL pública da app: config explícita ou a que o Render injeta."""
        return (settings.public_base_url or os.getenv("RENDER_EXTERNAL_URL") or "").rstrip("/")

    def _chart_link(self, device_id: int | None, loja_nome: str | None) -> str | None:
        base = self._base_url()
        if not base or device_id is None:
            return None
        loja = quote(loja_nome or "")
        return f"{base}/chart.html?device={device_id}&loja={loja}"

    # --- Normalização -----------------------------------------------------

    @staticmethod
    def _normalize_phone(phone: str | None) -> str | None:
        """Retorna telefone só com dígitos + DDI, ou None se inválido."""
        if not phone:
            return None
        digits = re.sub(r"\D", "", phone)
        if len(digits) < 10:  # telefone incompleto / inválido
            return None
        cc = re.sub(r"\D", "", settings.whatsapp_country_code) or "55"
        if not digits.startswith(cc):
            digits = cc + digits
        return digits

    # --- Mensagem ---------------------------------------------------------

    def build_message(
        self,
        device_id: int | None,
        loja_nome: str | None,
        severity: str,
        reason: str,
        rag_text: str | None,
    ) -> str:
        loja = loja_nome or "sua unidade"
        if severity == "critical":
            cabecalho = "🚨 *Alerta CRÍTICO Eletrofrio* 🚨"
            nivel = "crítica"
        else:
            cabecalho = "⚠️ *Alerta Eletrofrio* ⚠️"
            nivel = "de atenção"
        linhas = [
            cabecalho,
            f"Anomalia *{nivel}* detectada em {loja} (dispositivo {device_id}).",
            f"Motivo: {reason}",
        ]
        if rag_text:
            # rag_text pode vir com prefixo "[provider]\n" — pega o miolo
            corpo = rag_text.split("\n", 1)[-1].strip()
            if corpo:
                linhas.append(f"Recomendação: {corpo[:300]}")
        link = self._chart_link(device_id, loja_nome)
        if link:
            linhas.append(f"📈 Ver gráfico: {link}")
        return "\n".join(linhas)

    # --- Despacho ---------------------------------------------------------

    async def notify(
        self, phone: str | None, context: dict[str, Any]
    ) -> tuple[bool, dict[str, Any]]:
        """Retorna (enviado, resposta). Nunca levanta exceção."""
        # Override de demo: redireciona o envio para um número opt-in conhecido,
        # mantendo a mensagem com os dados reais da loja.
        target_raw = settings.whatsapp_override_phone or phone
        target = self._normalize_phone(target_raw)
        if not target:
            logger.info("[NotificationAgent] Sem telefone válido — pulando envio")
            return False, {"status": "skipped", "reason": "no_phone"}

        message = self.build_message(
            device_id=context.get("device_id"),
            loja_nome=context.get("loja_nome"),
            severity=context.get("severity", "warning"),
            reason=context.get("reason", ""),
            rag_text=context.get("rag_text"),
        )
        resp = await self.notifier.send(target, message)
        sent = resp.get("status") == "sent"
        resp = {**resp, "phone": target, "message": message}
        return sent, resp
