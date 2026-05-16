# Eletrofrio AI Backend

Sistema inteligente de suporte à manutenção de refrigeração comercial.
Consome a API Eletrofrio (hackathon), analisa telemetria/alarmes, usa
um **Orchestrator Agent** + **RAG Agent** para decidir entre
resposta direta, consulta técnica ou abertura de chamado.

## Stack
- Python 3.11+ / FastAPI
- MongoDB (motor, async) — persistência best-effort
- LangChain + Ollama/OpenAI (LLM opcional)
- RAG leve: TF-IDF + cosseno (stdlib pura, sem dependência pesada)

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
5. Se `warning` ou `critical` → chama **RAG Agent** (TF-IDF)
6. Se `critical` → abre chamado via `POST /abrir-chamado`
7. Retorna `AgentDecision` completo

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

Web Service Python

- **Build command:** `pip install -r requirements.txt`
- **Start command:** `python main.py` (a porta é lida de `$PORT`, injetada pelo Render)
- **Environment:** copie as chaves do `.env` (no mínimo `MONGO_URI`; `LLM_PROVIDER`
  vazio = modo extractive, sem precisar de Ollama/OpenAI no servidor)
- No **MongoDB Atlas → Network Access**, libere `0.0.0.0/0` (o IP do Render é dinâmico)

Sem `faiss`/`torch`: o RAG é TF-IDF puro, então roda no plano free sem estourar RAM.

## PoC — Como rodar localmente

1. Preencha `.env` com a connection string do MongoDB Atlas (`mongodb+srv://...`).
2. `python main.py` — aguarde os logs de boot e ping do Mongo.
3. Abra `http://localhost:8000/` — o mockup de celular renderiza com a lista de dispositivos.
4. Clique em qualquer dispositivo: a UI dispara `/api/analyze/{id}`, mostra severidade, gráfico de temperatura, alarmes recentes e (se aplicável) recomendação RAG + chamado aberto.

### Roteiro do vídeo demo (3 cenas)

1. **Boot e tela inicial:** subir a API, abrir `/` no browser, mostrar lista de devices coloridos (verde/amarelo/vermelho).
2. **Cenário OK + Warning:** clicar num device verde (resposta direta sem RAG) e depois num device amarelo (gráfico com pico, card RAG com recomendação).
3. **Cenário Critical:** clicar num device vermelho — badge piscando, card RAG e card de chamado com a resposta da API. Em seguida abrir o MongoDB Atlas e mostrar as coleções `agent_decisions` e `tickets` populadas.

## Endpoints
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/health` | Healthcheck (inclui ping Mongo) |
| GET | `/api/analyze/{device_id}` | **Fluxo principal** |
| GET | `/api/devices/summary` | Lista devices + última severidade (usado pela UI) |
| GET | `/api/alarms` | Proxy alarmes |
| GET | `/api/units` | Proxy unidades |
| GET | `/api/telemetry/{id}` | Proxy telemetria |
| POST | `/api/rag/query` | Query direta no RAG `{"query": "..."}` |
| GET | `/` | **Mockup mobile (PoC)** |

## LLM — provedores suportados

O RAG Agent escolhe o provedor via `LLM_PROVIDER` no `.env`:

| Valor | Comportamento |
|---|---|
| `ollama` (default) | LLM local via [Ollama](https://ollama.com), **sem custo, sem internet** |
| `openai` | Usa `gpt-4o-mini` (precisa de `OPENAI_API_KEY`) |
| (vazio) | Modo **extractive**: retorna os trechos da KB sem geração natural |


### Setup do Ollama (recomendado)

1. **Instalar Ollama Desktop**: baixe em https://ollama.com/download/windows e rode o instalador. Ele sobe um serviço local em `http://localhost:11434`.
2. **Baixar o modelo padrão** (≈ 2 GB, roda em CPU):
   ```powershell
   ollama pull llama3.2:3b
   ```
3. **Verificar**:
   ```powershell
   ollama list
   ```
4. **Reiniciar o `python main.py`** — nos logs deve aparecer:
   ```
   [RAG] LLM ativo: ollama:llama3.2:3b @ http://localhost:11434
   ```

## Logs
Todos os eventos importantes são logados via `loguru`:
- `[Orchestrator] Agente decidiu usar RAG`
- `[Orchestrator] Agente abriu chamado`
- `[Orchestrator] Anomalia crítica detectada`

## MongoDB — Coleções
- `telemetry_history` — snapshots de telemetria por análise
- `alarm_history` — snapshots de alarmes
- `agent_decisions` — decisão completa do Orchestrator
- `tickets` — chamados abertos automaticamente

## Referência aos agents-md
O **OrchestratorAgent** segue o espírito do `agents-orchestrator.md`:
pipeline sequencial, regras determinísticas antes do LLM, handoff claro
com contexto completo ao RagAgent. O `engineering-backend-architect.md`
guia a estrutura (Clean Architecture, separação de camadas, injeção de
dependência via FastAPI).
