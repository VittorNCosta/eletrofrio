"""Configurações globais carregadas do .env."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    eletrofrio_api_url: str = "https://credenciamento.eletrofrio.com.br:5900/galileo/api/api_hackathon"
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "eletrofrio"

    # LLM provider — "ollama" (local), "openai", ou "" (modo extractive sem IA)
    llm_provider: str = "ollama"
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    team_name: str = "AI Team"
    temperature_threshold: float = 10.0
    alarm_repeat_threshold: int = 3


settings = Settings()
