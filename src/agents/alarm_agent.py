"""Alarm Agent - filtra e analisa alarmes do dispositivo.

Responsabilidade única: dado o conjunto de alarmes brutos, isolar os do
dispositivo alvo, contar repetições por tag e sinalizar se o padrão é crítico.
"""
from collections import Counter
from typing import Any

from src.config import settings


class AlarmAgent:
    def analyze(self, alarms: list[dict[str, Any]], device_id: int) -> dict[str, Any]:
        device_alarms = [
            a for a in alarms
            if a.get("dispositivoId") == device_id or a.get("dispositivo_id") == device_id
        ]
        tags = [a.get("tag", "") for a in device_alarms]
        most_common = Counter(tags).most_common(1)
        repeats = most_common[0][1] if most_common else 0
        return {
            "device_alarms_count": len(device_alarms),
            "max_repeats": repeats,
            "critical_repeats": repeats >= settings.alarm_repeat_threshold,
            "device_alarms": device_alarms,
        }
