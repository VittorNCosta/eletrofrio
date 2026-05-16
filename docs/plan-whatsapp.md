# Sistema de Alertas WhatsApp para Anomalias de Dispositivo

## Contexto

Hoje o backend Eletrofrio classifica cada dispositivo em `ok | warning | critical` via `OrchestratorAgent`. Quando é `critical` (alarmes repetidos), o `TicketAgent` abre um chamado na API. **Falta o lado do cliente**: a loja/cliente não fica sabendo automaticamente que há uma anomalia no equipamento dela.

**Objetivo**: quando severity = `critical`, além de abrir o chamado, **enviar uma mensagem WhatsApp** para o telefone do cliente (recuperado de uma API adicional do hackathon, joinada por `loja_id`).

**Decisões já alinhadas com o usuário**:
- **Telefone**: vem de um endpoint adicional da API Eletrofrio (rota a confirmar — usaremos `settings.customers_route` configurável).
- **Provedor**: começa com **mock** (loga + persiste). Abstração permite plugar Twilio/Cloud API depois sem mexer no domínio.
- **Gatilho**: somente `severity == "critical"` (mesmo critério que já dispara abertura de chamado). Sem dedup nesta v1.

---

## Arquitetura — onde cada peça entra

Segue o padrão Clean Architecture já existente. Mudanças cirúrgicas, nada de refactor amplo.

### 1. Domínio — [src/domain/entities.py](../src/domain/entities.py)
Adicionar dois modelos e estender `AgentDecision`:
- **`Customer`** → `loja_id: int`, `nome: Optional[str]`, `telefone: Optional[str]`, `raw: dict` (mesmo padrão de `Unit`).
- **`Notification`** → `device_id`, `loja_id`, `phone`, `message`, `severity`, `status` (`"sent"|"failed"|"skipped"`), `provider`, `error?`, `sent_at` (default `utcnow`), `raw`.
- **`AgentDecision`** → novos campos `notification_sent: bool = False`, `notification_response: Optional[dict] = None`.

### 2. Configuração — [src/config.py](../src/config.py)
Adicionar em `Settings`:
- `customers_route: str = "clientes"` (placeholder — ajustável no `.env` quando confirmar a rota real).
- `whatsapp_provider: str = "mock"` (switch para o futuro).
- `whatsapp_notifications_enabled: bool = True` (kill-switch sem deploy).

### 3. Cliente HTTP externo — [src/infrastructure/external_api/eletrofrio_client.py](../src/infrastructure/external_api/eletrofrio_client.py)
Adicionar método `async fetch_customers()` espelhando `fetch_units()`:
- `await self._get({"route": settings.customers_route})`
- Mesmo tratamento `list-ou-{data:[...]}` já usado.
- Forma esperada: `[{"lojaId": int, "nome": str, "telefone": str, ...}]`.

### 4. Notifier Gateway — nova pasta `src/infrastructure/notifications/`
Abstração para isolar transporte:
- **`notifier_gateway.py`** → ABC `NotifierGateway` com `async send(phone, message) -> {"status", "provider", "raw"}`.
- **`whatsapp_mock.py`** → `WhatsAppMockNotifier(NotifierGateway)`: valida telefone, `logger.info("[WhatsAppMock] -> {phone}: {message}")`, retorna `status="sent"`. Sem I/O real. Persistência fica no caso de uso (responsabilidade única).
- **`__init__.py`** → re-exporta.

### 5. Novo agente — `src/agents/notification_agent.py`
`class NotificationAgent`:
- `__init__(self, notifier: NotifierGateway)`
- `build_message(device_id, loja_nome, reason, rag_text, ticket_response) -> str` → template PT-BR (referenciando id do chamado quando disponível).
- `async notify(customer_info, decision_context) -> tuple[bool, dict]`:
  - sem `telefone` → retorna `(False, {"status":"skipped","reason":"no_phone"})`.
  - caso contrário monta mensagem e chama `self.notifier.send(...)`.

Mantém o padrão "um agente, uma responsabilidade" do projeto (igual ao `TicketAgent`).

### 6. Orquestrador — [src/agents/orchestrator_agent.py](../src/agents/orchestrator_agent.py)
- Adicionar `notification_agent: NotificationAgent` no `__init__`.
- `analyze()` ganha parâmetro `customer_info: dict | None = None`.
- **Depois do bloco do ticket**, ainda dentro do `severity == "critical"`:
  - Respeitar `settings.whatsapp_notifications_enabled`.
  - Chamar `notifications.notify(customer_info, {device_id, loja_nome, reason, rag_text, ticket_response: resp if success else None})`.
  - Gravar `decision.notification_sent` e `decision.notification_response`.

Ordem é importante: ticket primeiro (despacho de técnico tem prioridade), notificação depois — assim a mensagem pode referenciar o id do chamado.

### 7. Caso de uso — [src/application/analyze_device.py](../src/application/analyze_device.py)
Em `execute()`:
- Após `alarms = await self.api.fetch_alarms()`, adicionar `customers = await self.api.fetch_customers()` em `try/except` → falha vira `customers = []` com log de warning (não derruba a análise).
- Novo helper `_resolve_customer(unit_info, customers) -> dict | None` que casa por `loja_id`.
- Passar `customer_info` para `self.orchestrator.analyze(...)`.
- Depois de `save_decision`, se `decision.notification_sent`, chamar `mongo.save_notification({...})`. Persistir também `status="failed"` para visibilidade de debug.

### 8. MongoDB — [src/infrastructure/database/mongo.py](../src/infrastructure/database/mongo.py)
- `async save_notification(self, doc)` → insere em `self.db.notifications` com `created_at = utcnow()`.
- `async find_recent_notifications(self, limit=50)` → ordenado por `created_at` desc, strip `_id`.
- Atualizar docstring com a nova coleção `notifications`.

### 9. Injeção de dependências — [src/interfaces/api/dependencies.py](../src/interfaces/api/dependencies.py)
Três novos providers `@lru_cache`:
- `get_notifier()` → switch em `settings.whatsapp_provider` (`"mock"` → `WhatsAppMockNotifier()`; default raise para forçar config explícita).
- `get_notification_agent()` → `NotificationAgent(notifier=get_notifier())`.
- Modificar `get_orchestrator()` para passar o `notification_agent`.

### 10. Rotas HTTP — [src/interfaces/api/routes.py](../src/interfaces/api/routes.py)
- `GET /customers` → proxy `await api.fetch_customers()` (debug).
- `GET /notifications?limit=50` → `await mongo.find_recent_notifications(limit)` (feed para o mockup mobile).

---

## Plano de verificação ponta-a-ponta

1. Configurar `.env` com `CUSTOMERS_ROUTE=<rota_real>` e `WHATSAPP_PROVIDER=mock`.
2. `python main.py` → conferir que sobe sem erro (sem regressão).
3. `GET /api/devices/summary` → escolher um device cujos alarmes repetem ≥ `alarm_repeat_threshold` (será `critical`).
4. `GET /api/analyze/{device_id}` → JSON esperado: `severity="critical"`, `ticket_opened=true`, **`notification_sent=true`**, `notification_response.status="sent"`.
5. Logs (loguru) devem mostrar `[WhatsAppMock] -> <telefone>: Alerta critico Eletrofrio ...`.
6. MongoDB: `db.notifications.find().sort({created_at:-1}).limit(1)` retorna o documento com mensagem + telefone.
7. `GET /api/notifications` retorna a nova entrada no topo.
8. **Caminho negativo (sem telefone)**: device crítico cuja `lojaId` não tem cliente cadastrado → `notification_sent=false`, `notification_response={"status":"skipped","reason":"no_phone"}`.
9. **Severidade ok/warning**: confirmar que `notification_sent` permanece `false` (não entra no bloco).

---

## Trade-offs assumidos (e como destravar depois)

- **Mock-only por design**: nenhuma mensagem real é enviada. Para plugar um provedor real, **criar um único arquivo** (ex. `whatsapp_twilio.py` implementando `NotifierGateway`), registrar em `get_notifier()` e mudar `WHATSAPP_PROVIDER=twilio`. **Zero mudança em domínio/caso de uso** — esse é o valor do gateway.
- **Rota `customers_route` é palpite (`"clientes"`)**: precisa ser confirmada pelo contrato real da API do hackathon e ajustada no `.env`. Se o payload vier com formato diferente, normalizar dentro de `fetch_customers()` apenas.
- **Sem retry/dedup nesta v1**: cada chamada de `/analyze` em device crítico envia uma mensagem nova. Follow-up natural: consultar `notifications` por `last_sent_at` e suprimir reenvio em janela de N minutos.
- **Falha ao buscar clientes degrada silenciosamente**: outage da API de clientes → `customers=[]` → notificação é "skipped", ticket continua sendo aberto. Intencional (ticket é prioridade maior).
