"""Base de conhecimento mock para RAG.

Contém diagnósticos técnicos frequentes de refrigeração comercial.
Em produção: alimentar com manuais reais + histórico de chamados.
"""

KNOWLEDGE_BASE: list[dict[str, str]] = [
    {
        "title": "Temperatura alta em câmara fria",
        "content": (
            "Se a temperatura da câmara ultrapassa 10°C por mais de 30 minutos, "
            "verifique: (1) porta mal fechada ou vedação danificada; (2) degelo "
            "prolongado (> 45min pode indicar sensor com falha); (3) sujeira no "
            "condensador; (4) carga de gás refrigerante baixa. Recomendação: "
            "inspeção técnica presencial se persistir."
        ),
    },
    {
        "title": "Excesso de tempo em degelo",
        "content": (
            "Degelo prolongado normalmente é causado por sensor de fim de degelo "
            "com defeito, resistência queimada ou timer descalibrado. Ação: "
            "abrir chamado técnico, pois risco de perda de produto é alto."
        ),
    },
    {
        "title": "Alarmes recorrentes de alta temperatura",
        "content": (
            "Alarmes repetidos no mesmo dispositivo em curto intervalo indicam "
            "falha sistêmica. Não adianta reset remoto — requer diagnóstico "
            "presencial. Abrir chamado como CRÍTICO."
        ),
    },
    {
        "title": "Oscilação de temperatura normal",
        "content": (
            "Oscilações de até 3°C durante ciclos de degelo são normais. "
            "Se estabiliza em até 20 min, não requer ação."
        ),
    },
    {
        "title": "Falha de comunicação do dispositivo",
        "content": (
            "Quando não há telemetria recente, pode ser queda de rede local "
            "ou falha do controlador. Verificar ping; se offline > 1h, abrir chamado."
        ),
    },
    {
        "title": "Expositores de açougue/frios",
        "content": (
            "Expositores de açougue devem operar entre 0°C e 4°C. Acima de 6°C "
            "é risco sanitário — ação imediata, abrir chamado crítico."
        ),
    },
]
