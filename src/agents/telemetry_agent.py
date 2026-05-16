"""Telemetry Agent - normaliza e analisa leituras de telemetria.

Responsabilidade única: a partir do payload bruto da API Eletrofrio
(formato Chart.js: {labels, datasets:[{label,color,values}]}), extrair a
série de Temperatura Ambiente e calcular estatísticas prontas para
classificação (max, avg, flag de temperatura alta).
"""
from typing import Any

from src.config import settings


class TelemetryAgent:
    # Para retrocompatibilidade com formato antigo (list[dict])
    _LEGACY_TEMP_KEYS = ("temperatura", "temp", "valor", "value")

    def analyze(self, telemetry: Any) -> dict[str, Any]:
        temps = self._extract_temps(telemetry)
        if not temps:
            return {"max_temp": None, "avg_temp": None, "high_temp_alert": False}

        max_t = max(temps)
        return {
            "max_temp": max_t,
            "avg_temp": sum(temps) / len(temps),
            "high_temp_alert": max_t > settings.temperature_threshold,
        }

    def _extract_temps(self, telemetry: Any) -> list[float]:
        # Formato atual: dict com `datasets`
        if isinstance(telemetry, dict):
            for ds in telemetry.get("datasets", []) or []:
                label = (ds.get("label") or "").lower()
                if "temperatura" in label and "setpoint" not in label:
                    return [
                        float(v)
                        for v in (ds.get("values") or [])
                        if isinstance(v, (int, float))
                    ]
            return []

        # Formato legado: list[dict]
        temps: list[float] = []
        for row in telemetry or []:
            if not isinstance(row, dict):
                continue
            for key in self._LEGACY_TEMP_KEYS:
                v = row.get(key)
                if isinstance(v, (int, float)):
                    temps.append(float(v))
                    break
        return temps
