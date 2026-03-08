"""Configuração via variáveis de ambiente."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Suno
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

    # YouTube
    google_client_secrets_path: Path = Path("./client_secrets.json")
    youtube_category_id: str = "10"  # Music
    youtube_privacy_status: str = "private"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        self.output_videos_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
