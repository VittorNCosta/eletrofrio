"""Configurações globais carregadas do .env."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    eletrofrio_api_url: str = "https://credenciamento.eletrofrio.com.br:5900/galileo/api/api_hackathon"
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "eletrofrio"

    # LLM provider — "groq" (grátis na nuvem), "ollama" (local), "openai",
    # ou "" (modo extractive sem IA)
    llm_provider: str = "groq"
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # URL pública da aplicação (usada nos links enviados no WhatsApp).
    # Vazio em produção cai no RENDER_EXTERNAL_URL (injetado pelo Render).
    public_base_url: str = ""

    # WhatsApp / alertas ao cliente
    whatsapp_enabled: bool = True
    whatsapp_provider: str = "callmebot"  # "callmebot" | "mock"
    callmebot_apikey: str = ""
    # Demo: se preenchido, todos os alertas vão para este número (já opt-in no
    # CallMeBot), mas a mensagem segue citando a loja/cliente real.
    whatsapp_override_phone: str = ""
    whatsapp_country_code: str = "55"

    team_name: str = "AI Team"
    temperature_threshold: float = 10.0
    alarm_repeat_threshold: int = 3


settings = Settings()
