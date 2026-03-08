"""Configuração via variáveis de ambiente."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Suno: API sunoapi.org (recomendado) ou lib SunoAI com cookie
    sunoapi_key: str = ""  # Bearer token de https://sunoapi.org/api-key
    sunoapi_base_url: str = "https://api.sunoapi.org"
    suno_cookie: str = ""

    # API
    api_key: str = ""

    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_generate: str = "music-generation-requests"
    kafka_topic_publish: str = "video-ready-for-youtube"

    # Paths
    work_dir: Path = Path("./work")
    downloads_dir: Path = Path("./downloads")
    output_videos_dir: Path = Path("./output_videos")

    # YouTube (a API não aceita channelId no upload; o canal é o da conta das credenciais)
    google_client_secrets_path: Path = Path("./client_secrets.json")
    youtube_credentials_path: str = ""  # opcional: path do credentials.json (conta/canal). Vazio = ao lado do client_secrets
    youtube_category_id: str = "10"  # Music
    youtube_privacy_status: str = "private"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        self.output_videos_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
