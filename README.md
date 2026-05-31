# Eletrofrio AI Backend

Sistema inteligente de suporte à manutenção de refrigeração comercial.
Consome a API Eletrofrio (hackathon), analisa telemetria/alarmes, usa
um **Orchestrator Agent** + **RAG Agent** para classificar severidade,
gerar recomendação técnica e **alertar o cliente via WhatsApp** (com o
link do gráfico do dispositivo).

## Stack
- Python 3.11+ / FastAPI
- MongoDB (motor, async) — persistência best-effort
- LangChain + **Groq** (LLM grátis na nuvem) / Ollama / OpenAI
- RAG leve: TF-IDF + cosseno (stdlib pura, sem dependência pesada)
- Alertas: **WhatsApp via CallMeBot** (grátis)

## Arquitetura (Clean Architecture / DDD leve)
```
src/
├── domain/              # Entidades do negócio (Alarm, Telemetry, Decision)
├── application/         # Casos de uso (AnalyzeDeviceUseCase)
├── infrastructure/
│   ├── external_api/    # Cliente HTTP Eletrofrio
│   ├── database/        # MongoDB
│   └── rag/             # TF-IDF store + knowledge base
├── agents/              # OrchestratorAgent + RagAgent
└── interfaces/api/      # FastAPI (rotas, deps, app)
```

## Fluxo
1. `GET /api/analyze/{device_id}`
2. Backend busca **telemetria** + **alarmes** na API externa
3. Persiste histórico no MongoDB
4. Orchestrator aplica **regras determinísticas**:
   - `temperatura > 10°C` → warning
   - alarmes repetidos (≥3x) → critical
   - dados inconsistentes → warning (RAG)
5. Se `warning` ou `critical` → chama **RAG Agent** (TF-IDF + Groq) e
   **envia alerta WhatsApp** ao telefone da loja (endpoint `unidades`),
   com o link do gráfico do dispositivo
6. Retorna `AgentDecision` completo

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env 
python main.py
```

- API: `http://localhost:8000/docs`
- **PoC (mockup mobile): `http://localhost:8000/`**

> Dev local com auto-reload: `DEV_RELOAD=1` no `.env`.

## Deploy (Render)

Web Service Python (há um `render.yaml` na raiz como Blueprint).

- **Build command:** `pip install -r requirements.txt`
- **Start command:** `python main.py` (a porta é lida de `$PORT`, injetada pelo Render)
- **Branch:** `develop`
- **Environment** (Settings → Environment) — cadastre as variáveis (segredos não
  vão no git):

  ```
  LLM_PROVIDER=groq
  GROQ_API_KEY=<sua chave Groq>
  WHATSAPP_ENABLED=true
  WHATSAPP_PROVIDER=callmebot
  CALLMEBOT_APIKEY=<sua apikey CallMeBot>
  WHATSAPP_OVERRIDE_PHONE=<seu número p/ demo>
  WHATSAPP_COUNTRY_CODE=55
  MONGO_URI=<connection string Atlas>
  # PUBLIC_BASE_URL pode ficar vazio: o Render injeta RENDER_EXTERNAL_URL
  ```
- No **MongoDB Atlas → Network Access**, libere `0.0.0.0/0` (o IP do Render é dinâmico)
- Após push na `develop` o deploy dispara automaticamente (ou use **Manual Deploy**)

Sem `faiss`/`torch`: o RAG é TF-IDF puro, então roda no plano free sem estourar RAM.

## PoC — Como rodar localmente

1. Preencha `.env` com a connection string do MongoDB Atlas (`mongodb+srv://...`).
2. `python main.py` — aguarde os logs de boot e ping do Mongo.
3. Abra `http://localhost:8000/` — o mockup de celular renderiza com a lista de dispositivos.
4. Clique em qualquer dispositivo: a UI dispara `/api/analyze/{id}`, mostra severidade, gráfico de temperatura, alarmes recentes e (se aplicável) recomendação RAG + status do alerta WhatsApp enviado.

### Roteiro do vídeo demo (3 cenas)

1. **Boot e tela inicial:** subir a API, abrir `/` no browser, mostrar lista de devices coloridos (verde/amarelo/vermelho).
2. **Cenário OK + Warning:** clicar num device verde (resposta direta sem RAG) e depois num device amarelo (gráfico com pico, card RAG com recomendação, alerta WhatsApp enviado).
3. **Cenário Critical + Mobile:** clicar num device vermelho — badge, card RAG e card verde "alerta enviado". Mostrar o **WhatsApp chegando no celular** com o link, tocar no link e abrir o gráfico full-screen. Em seguida abrir o MongoDB Atlas e mostrar as coleções `agent_decisions` e `notifications` populadas.

## Endpoints
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/health` | Healthcheck (inclui ping Mongo) |
| GET | `/api/analyze/{device_id}` | **Fluxo principal** |
| GET | `/api/devices/summary` | Lista devices + última severidade (usado pela UI) |
| GET | `/api/alarms` | Proxy alarmes |
| GET | `/api/units` | Proxy unidades |
| GET | `/api/telemetry/{id}` | Proxy telemetria |
| GET | `/api/notifications` | Alertas WhatsApp recentes (feed/debug) |
| POST | `/api/rag/query` | Query direta no RAG `{"query": "..."}` |
| GET | `/` | **Mockup mobile (PoC)** |
| GET | `/chart.html?device={id}` | **Gráfico full-screen** (link enviado no WhatsApp) |

## LLM — provedores suportados

O RAG Agent escolhe o provedor via `LLM_PROVIDER` no `.env`:

| Valor | Comportamento |
|---|---|
| `groq` (default) | LLM grátis na nuvem (`llama-3.3-70b-versatile`); precisa de `GROQ_API_KEY` ([console.groq.com](https://console.groq.com)) |
| `ollama` | LLM local via [Ollama](https://ollama.com), **sem custo, sem internet** |
| `openai` | Usa `gpt-4o-mini` (precisa de `OPENAI_API_KEY`) |
| (vazio) | Modo **extractive**: retorna os trechos da KB sem geração natural |


### Setup do Groq (default, recomendado)

1. Crie uma chave em [console.groq.com](https://console.groq.com) → *API Keys*.
2. No `.env`: `LLM_PROVIDER=groq` e `GROQ_API_KEY=gsk_...`.
3. **Reiniciar o `python main.py`** — nos logs deve aparecer:
   ```
   [RAG] LLM ativo: groq:llama-3.3-70b-versatile
   ```

> Alternativa offline: `LLM_PROVIDER=ollama` com [Ollama](https://ollama.com)
> instalado (`ollama pull llama3.2:3b`).

### Setup do WhatsApp (CallMeBot, grátis)

1. No WhatsApp, salve **+34 644 51 95 23** e envie `I allow callmebot to send me messages`.
2. O bot responde com sua **apikey**. No `.env`: `CALLMEBOT_APIKEY=...`.
3. Para a demo, aponte `WHATSAPP_OVERRIDE_PHONE` para o número que ativou o bot
   (só ele recebe — limitação do CallMeBot grátis).

## Logs
Todos os eventos importantes são logados via `loguru`:
- `[Orchestrator] Delegando ao RAG Agent`
- `[Orchestrator] Delegando ao Notification Agent`
- `[CallMeBot] -> <telefone>: ...`

## MongoDB — Coleções
- `telemetry_history` — snapshots de telemetria por análise
- `alarm_history` — snapshots de alarmes
- `agent_decisions` — decisão completa do Orchestrator
- `notifications` — alertas WhatsApp enviados (status, telefone, mensagem)

## Referência aos agents-md
O **OrchestratorAgent** segue o espírito do `agents-orchestrator.md`:
pipeline sequencial, regras determinísticas antes do LLM, handoff claro
com contexto completo ao RagAgent. O `engineering-backend-architect.md`
guia a estrutura (Clean Architecture, separação de camadas, injeção de
dependência via FastAPI).
