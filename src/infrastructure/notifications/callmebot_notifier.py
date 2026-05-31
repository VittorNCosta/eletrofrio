"""CallMeBot - envio real de WhatsApp via requisição HTTP simples (grátis).

Endpoint: https://api.callmebot.com/whatsapp.php?phone=<E164>&text=<msg>&apikey=<key>

Limitação do CallMeBot: o número destino precisa ter ativado o bot uma vez e
possuir uma apikey pessoal. Para a demo, use WHATSAPP_OVERRIDE_PHONE apontando
para um número já ativado (a mensagem segue citando a loja real).
"""
from typing import Any

import httpx
from loguru import logger

from src.config import settings
from src.infrastructure.notifications.notifier_gateway import NotifierGateway

CALLMEBOT_URL = "https://api.callmebot.com/whatsapp.php"


class CallMeBotNotifier(NotifierGateway):
    def __init__(self, apikey: str | None = None, timeout: float = 20.0):
        self.apikey = apikey if apikey is not None else settings.callmebot_apikey
        self._timeout = timeout

    async def send(self, phone: str, message: str) -> dict[str, Any]:
        if not self.apikey:
            logger.warning("[CallMeBot] apikey ausente — envio ignorado")
            return {"status": "failed", "provider": "callmebot", "error": "no_apikey"}

        params = {"phone": phone, "text": message, "apikey": self.apikey}
        logger.info(f"[CallMeBot] -> {phone}: {message[:80]}...")
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                r = await client.get(CALLMEBOT_URL, params=params)
            body = r.text
            # CallMeBot devolve HTTP 203 tanto em sucesso quanto em erro; o que
            # vale é o corpo. Falha quando há marcador de erro (ex.: "invalid").
            low = body.lower()
            failed = (
                r.status_code >= 400
                or "invalid" in low
                or "color:red" in low
                or "not allowed" in low
                or "error" in low
            )
            status = "failed" if failed else "sent"
            if failed:
                logger.warning(f"[CallMeBot] Recusado (HTTP {r.status_code}): {body[:200]}")
            return {
                "status": status,
                "provider": "callmebot",
                "http_status": r.status_code,
                "raw": body[:500],
            }
        except Exception as e:
            logger.error(f"[CallMeBot] Falha no envio: {e}")
            return {"status": "failed", "provider": "callmebot", "error": str(e)}
