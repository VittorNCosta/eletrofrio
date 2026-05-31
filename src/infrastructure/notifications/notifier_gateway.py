"""Gateway de notificação - abstrai o transporte (WhatsApp, etc.).

Isola o domínio do provedor concreto: o NotificationAgent fala apenas com esta
interface, então trocar CallMeBot por Twilio/Meta é só adicionar uma nova
implementação e registrá-la na injeção de dependências (get_notifier).
"""
from abc import ABC, abstractmethod
from typing import Any


class NotifierGateway(ABC):
    """Contrato mínimo de envio de mensagem."""

    @abstractmethod
    async def send(self, phone: str, message: str) -> dict[str, Any]:
        """Envia `message` para `phone`.

        Retorna dict com pelo menos: {"status": "sent"|"failed", "provider": str}.
        Implementações não devem levantar exceção — falhas viram status="failed".
        """
        raise NotImplementedError
