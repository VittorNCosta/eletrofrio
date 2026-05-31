"""RAG Agent - recupera conhecimento técnico e gera recomendação.

Fluxo:
1. Recebe query (descrição do problema)
2. Busca top-k no FAISS
3. Monta prompt com contexto e pede diagnóstico ao LLM
4. Fallback: se nenhum LLM estiver acessível, retorna os trechos
   da KB concatenados (modo "extractive").

Provedores suportados (escolhidos via settings.llm_provider):
- "groq"   → API da Groq (grátis na nuvem, compatível com OpenAI)
- "ollama" → LLM local via Ollama (sem custo, sem internet)
- "openai" → API da OpenAI (gpt-4o-mini por padrão)
- ""       → modo extractive (sem IA generativa)
"""
from loguru import logger

from src.config import settings
from src.infrastructure.rag.keyword_store import KnowledgeStore


PROMPT_TEMPLATE = (
    "Você é um técnico especialista em refrigeração comercial. "
    "Com base no CONTEXTO abaixo, diagnostique o problema e "
    "recomende uma ação concreta (em até 4 linhas, em português). "
    "Não use a expressão \"abrir chamado\"; prefira \"acionar a equipe técnica\" "
    "ou \"acionar a manutenção\".\n\n"
    "CONTEXTO:\n{context}\n\n"
    "PROBLEMA: {query}\n\n"
    "DIAGNÓSTICO E RECOMENDAÇÃO:"
)


class RagAgent:
    def __init__(self):
        self.store = KnowledgeStore.get_instance()
        self._llm = None
        self._provider_name = "extractive"
        self._init_llm()

    def _init_llm(self) -> None:
        provider = (settings.llm_provider or "").lower().strip()

        if provider == "groq" and settings.groq_api_key:
            try:
                from langchain_openai import ChatOpenAI
                self._llm = ChatOpenAI(
                    model=settings.groq_model,
                    api_key=settings.groq_api_key,
                    base_url="https://api.groq.com/openai/v1",
                    temperature=0.2,
                )
                self._provider_name = f"groq:{settings.groq_model}"
                logger.info(f"[RAG] LLM ativo: {self._provider_name}")
                return
            except Exception as e:
                logger.warning(f"[RAG] Groq indisponível ({e}). Fallback extractive.")

        if provider == "ollama":
            try:
                from langchain_ollama import ChatOllama
                self._llm = ChatOllama(
                    base_url=settings.ollama_host,
                    model=settings.ollama_model,
                    temperature=0.2,
                )
                self._provider_name = f"ollama:{settings.ollama_model}"
                logger.info(f"[RAG] LLM ativo: {self._provider_name} @ {settings.ollama_host}")
                return
            except Exception as e:
                logger.warning(f"[RAG] Ollama indisponível ({e}). Fallback extractive.")

        if provider == "openai" and settings.openai_api_key:
            try:
                from langchain_openai import ChatOpenAI
                self._llm = ChatOpenAI(
                    model=settings.openai_model,
                    api_key=settings.openai_api_key,
                    temperature=0.2,
                )
                self._provider_name = f"openai:{settings.openai_model}"
                logger.info(f"[RAG] LLM ativo: {self._provider_name}")
                return
            except Exception as e:
                logger.warning(f"[RAG] OpenAI indisponível ({e}). Fallback extractive.")

        logger.info("[RAG] Sem LLM configurado — modo extractive")

    async def diagnose(self, query: str, k: int = 3) -> str:
        docs = self.store.search(query, k=k)
        if not docs:
            return "Nenhum conhecimento técnico relevante encontrado."

        context = "\n\n".join(f"- {d['title']}: {d['content']}" for d in docs)

        if self._llm is None:
            return (
                f"[Modo extractive — sem LLM configurado]\n"
                f"Trechos relevantes encontrados:\n{context}"
            )

        prompt = PROMPT_TEMPLATE.format(context=context, query=query)
        try:
            resp = await self._llm.ainvoke(prompt)
            text = resp.content if hasattr(resp, "content") else str(resp)
            return f"[{self._provider_name}]\n{text.strip()}"
        except Exception as e:
            logger.error(f"[RAG] Falha no LLM ({self._provider_name}): {e}")
            return (
                f"[Erro no LLM — fallback extractive]\n"
                f"Trechos relevantes:\n{context}"
            )
