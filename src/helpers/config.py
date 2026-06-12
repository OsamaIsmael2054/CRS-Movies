from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# src/helpers/config.py -> parents[2] == repo root.
REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            REPO_ROOT / "docker" / "env" / ".env.postgres",
            REPO_ROOT / "docker" / "env" / ".env.app",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str
    postgres_host_port: int

    data_dir: Path = REPO_ROOT / "src" / "assets" / "Movie"

    cf_top_m: int = 50
    cf_top_k: int = 20
    cf_user_neighbors: int = 50

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma4:12b"
    ollama_timeout: float = 120.0
    ollama_temperature: float = 0.3
    ollama_think: bool | str = False

    @property
    def repo_root(self) -> Path:
        return REPO_ROOT

    @property
    def schema_path(self) -> Path:
        return REPO_ROOT / "db" / "schema.sql"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_host_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
