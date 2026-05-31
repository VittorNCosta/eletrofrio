# Prova de Conceito — Eletrofrio AI

**Solução inteligente de suporte à manutenção de refrigeração comercial**

| | |
|---|---|
| **Equipe** | _[preencher: nome da equipe / integrantes]_ |
| **Disciplina / Professor** | _[preencher]_ |
| **Data** | 15/05/2026 |
| **Aplicação hospedada** | https://eletrofrio.onrender.com |
| **Repositório (código-fonte)** | https://github.com/VittorNCosta/eletrofrio |

> Documento referente à entrega da Prova de Conceito (PoC) conforme `docs/POC.md`.
> A parte técnica (código, instruções de execução) está no repositório; este
> documento cobre a estruturação conceitual e os entregáveis.

---

## 1. Questão de pesquisa

> Como utilizar os dados de telemetria e de alarmes de equipamentos de
> refrigeração comercial para **classificar automaticamente a criticidade**
> de cada dispositivo e **priorizar a intervenção técnica**, reduzindo perda
> de produto, risco sanitário e tempo de resposta da manutenção?

A questão parte de um problema concreto do domínio: redes de varejo e centros
de distribuição operam grandes frotas de equipamentos de frio (expositores,
câmaras frias, balcões de açougue/congelados). Esses equipamentos geram
telemetria e alarmes continuamente, mas o volume de dados raramente é
convertido em **ação priorizada** — a manutenção tende a ser reativa.

## 2. Objetivo geral

Desenvolver uma solução que consuma dados reais de telemetria e alarmes da
API Eletrofrio, organize essas informações, **classifique a severidade** de
cada dispositivo de forma determinística e, quando necessário, **recomende
ação técnica** e **alerte o cliente automaticamente via WhatsApp** (com o link
do gráfico do dispositivo), oferecendo uma interface de visualização para o
time de operação.

## 3. Objetivos específicos

1. Consumir e integrar os endpoints da API Eletrofrio (`telemetria`,
   `alarmes`, `unidades`).
2. Tratar e organizar os dados brutos (estatísticas de temperatura,
   contagem e padrões de alarmes, enriquecimento com loja/dispositivo).
3. Implementar classificação determinística de severidade
   (`ok` / `warning` / `critical`) com regras de negócio explícitas.
4. Estruturar uma base de conhecimento técnico e recuperar trechos
   relevantes via RAG (TF-IDF + similaridade de cosseno) com geração por LLM (Groq).
5. Automatizar o alerta ao cliente via WhatsApp (telefone obtido em `unidades`)
   nos casos de `warning` e `critical`, incluindo o link do gráfico.
6. Persistir o histórico (telemetria, alarmes, decisões, notificações) para
   rastreabilidade.
7. Entregar uma interface funcional (mockup mobile responsivo) com visualização
   (gráfico de temperatura, indicadores e badge de severidade).

## 4. Justificativa

Falhas de refrigeração têm impacto direto e mensurável:

- **Perda de produto** — excursão de temperatura em congelados/resfriados
  inutiliza mercadoria.
- **Risco sanitário** — expositores de açougue/frios acima do limite
  representam risco à saúde do consumidor.
- **Custo de manutenção reativa** — sem priorização, equipes atendem
  chamados na ordem errada e o tempo médio de reparo (MTTR) cresce.

Os dados necessários para antecipar esses problemas **já existem** (telemetria
e alarmes), mas não são transformados em triagem priorizada. Uma camada
automatizada de classificação + recomendação + alerta ao cliente reduz
perdas e acelera a resposta, atuando como um **assistente de triagem** para
a equipe técnica.

## 5. Contexto de aplicação

Redes de supermercados e centros de distribuição com frotas de equipamentos
de frio distribuídas em múltiplas lojas. O público-alvo é o **time de
operação/manutenção**, sobrecarregado pelo volume de alarmes. A solução se
posiciona como assistente que diz **onde olhar primeiro** e **o que
provavelmente fazer**, alertando o cliente via WhatsApp nos casos relevantes.

## 6. Coerência: problema → solução

| Problema | Objetivo | Dados usados | Funcionalidade implementada |
|---|---|---|---|
| Volume de alarmes sem priorização | Classificar severidade | `alarmes`, `telemetria` | Orchestrator com regras determinísticas (`ok`/`warning`/`critical`) |
| Não saber a causa provável | Recomendar ação | Base de conhecimento + contexto do device | RAG Agent (TF-IDF + LLM Groq) retorna diagnóstico técnico |
| Demora para avisar o cliente | Automatizar alerta | severidade + telefone da loja (`unidades`) | Notification Agent envia WhatsApp (CallMeBot) com link do gráfico |
| Falta de rastreabilidade | Persistir histórico | telemetria/alarmes/decisões | MongoDB (`agent_decisions`, `notifications`, etc.) |
| Operação sem visão rápida | Interface funcional | resultado consolidado | Mockup mobile responsivo: lista com cores de severidade, gráfico, alarmes |

## 7. Atendimento aos requisitos mínimos da PoC

Conforme `docs/POC.md`, seção "A entrega mínima da PoC deverá conter":

| # | Requisito | Como foi atendido |
|---|---|---|
| 1 | Consumo funcional de ≥1 endpoint | Consome 3 endpoints da API Eletrofrio (`telemetria`, `alarmes`, `unidades`) validados ao vivo |
| 2 | Organização/tratamento dos dados | Estatísticas de temperatura, padrões de alarme, enriquecimento loja/dispositivo |
| 3 | Interface funcional | Mockup mobile responsivo servido em `/` + gráfico full-screen em `/chart.html` |
| 4 | Visualização/painel/indicador | Gráfico de temperatura (Chart.js), métricas máx/méd/mín, badge de severidade |
| 5 | Análise/funcionalidade da proposta | Pipeline Orchestrator → classificação → RAG (Groq) → alerta WhatsApp com link do gráfico |

## 8. Arquitetura e stack (resumo)

- **Backend:** Python 3.12 / FastAPI (Clean Architecture / DDD leve)
- **Persistência:** MongoDB Atlas (gravação *best-effort* — indisponibilidade
  do banco não derruba a aplicação)
- **RAG:** recuperação por TF-IDF + cosseno (stdlib pura, sem dependência
  pesada); geração por LLM via **Groq** (grátis na nuvem), com *fallback*
  extractivo quando não há LLM configurado
- **Alertas:** WhatsApp via **CallMeBot** (grátis); telefone obtido em
  `unidades`, dispara em `warning`/`critical`, com link do gráfico
- **Frontend:** mockup mobile responsivo (HTML/CSS/JS + Chart.js) + página de
  gráfico full-screen
- **Hospedagem:** Render (Web Service)

> Detalhes de fluxo, endpoints e instruções de execução estão no `README.md`
> do repositório.

## 9. Limitações conhecidas (honestidade técnica)

- A geração por LLM usa o **Groq** (grátis); sem chave configurada, o RAG cai
  automaticamente para **modo extractivo** (trechos da base, sem geração).
- O **CallMeBot** (WhatsApp grátis) só entrega a números que ativaram o bot;
  na demo, os alertas são redirecionados a um número de teste (`WHATSAPP_OVERRIDE_PHONE`),
  mantendo a mensagem com os dados reais da loja. Em produção, usaria um provedor
  oficial (Twilio/Meta Cloud API) sem mudar o domínio.
- A base de conhecimento é um conjunto inicial de diagnósticos; em produção
  seria alimentada com manuais e histórico real.
- O plano gratuito de hospedagem hiberna após inatividade (primeira
  requisição pode levar ~50s).

## 10. Entregáveis

| Entregável | Link / Localização |
|---|---|
| Aplicação hospedada (acesso e testes) | https://eletrofrio.onrender.com |
| Repositório com código-fonte | https://github.com/VittorNCosta/eletrofrio |
| Instruções de execução | `README.md` (no repositório) |
| Enunciado da atividade | `docs/POC.md` (no repositório) |

### Como testar rapidamente

1. Acesse https://eletrofrio.onrender.com (aguarde ~50s se estiver hibernado),
   de preferência **pelo celular**.
2. A lista de dispositivos carrega a partir dos alarmes reais da API.
3. Clique em um dispositivo: a aplicação dispara a análise e exibe
   severidade, gráfico de temperatura, alarmes e recomendação técnica (Groq).
4. Em `warning`/`critical`, um **alerta de WhatsApp** é enviado ao telefone da
   loja com o **link do gráfico** — toque no link para abrir o gráfico full-screen
   no próprio celular.
