"""WhatsApp mock - apenas loga (sem I/O real). Útil para dev/CI."""
from typing import Any

from loguru import logger

from src.infrastructure.notifications.notifier_gateway import NotifierGateway


class WhatsAppMockNotifier(NotifierGateway):
    async def send(self, phone: str, message: str) -> dict[str, Any]:
        logger.info(f"[WhatsAppMock] -> {phone}: {message}")
        return {"status": "sent", "provider": "mock", "raw": "mock-no-op"}
