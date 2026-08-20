"""Configuração da aplicação, carregada do ambiente."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Banco
    database_url: str = "postgresql+psycopg://verzel:verzel@localhost:5432/verzel_ingressos"

    # Autenticação de usuário
    jwt_secret: str = "dev-jwt-secret-nao-usar-em-producao"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 480

    # Assinatura do ingresso. Segredo separado do JWT de propósito: comprometer
    # a sessão de um usuário não pode dar o poder de forjar ingressos.
    ticket_secret: str = "dev-ticket-secret-nao-usar-em-producao"

    # Catálogo externo
    catalog_provider: str = "tmdb"  # "tmdb" | "fixture"
    tmdb_base_url: str = "https://api.themoviedb.org/3"
    tmdb_image_base_url: str = "https://image.tmdb.org/t/p"
    tmdb_language: str = "pt-BR"
    tmdb_read_token: str = ""
    catalog_cache_ttl: int = 600

    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
