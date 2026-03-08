"""Schemas Pydantic para API e mensagens Kafka."""
from typing import Any

from pydantic import BaseModel, Field


# ----- API: entrada para gerar música -----
class GenerateMusicRequest(BaseModel):
    """Payload recebido no POST /generate ou na fila Kafka."""

    title: str = Field(..., description="Título da música")
    lyrics: str = Field(..., description="Letra da música (usada como prompt no Suno)")
    genre: str = Field(default="", description="Gênero/tags (ex: 'pop, male voice')")
    make_instrumental: bool = Field(default=False, description="Gerar versão instrumental")
    model_version: str = Field(default="chirp-v3-5", description="Modelo Suno: chirp-v3-5, chirp-v3-0, chirp-v2-0")
    youtube_credentials_path: str = Field(default="", description="Opcional: path do credentials.json do canal onde publicar no YouTube")


# ----- Resposta do Suno (Clip simplificado para nossa API) -----
class SunoSongInfo(BaseModel):
    """Dados de uma música gerada pelo Suno."""

    id: str
    title: str
    audio_url: str
    image_url: str
    image_large_url: str = ""
    status: str = ""

    @classmethod
    def from_clip(cls, clip: Any) -> "SunoSongInfo":
        return cls(
            id=getattr(clip, "id", "") or str(clip.get("id", "")),
            title=getattr(clip, "title", "") or str(clip.get("title", "")),
            audio_url=getattr(clip, "audio_url", "") or str(clip.get("audio_url", "")),
            image_url=getattr(clip, "image_url", "") or str(clip.get("image_url", "")),
            image_large_url=getattr(clip, "image_large_url", "") or str(clip.get("image_large_url", "")),
            status=getattr(clip, "status", "") or str(clip.get("status", "")),
        )

    @classmethod
    def from_sunoapi_item(cls, item: dict) -> "SunoSongInfo":
        """Converte um item de data.response.sunoData da API sunoapi.org (camelCase)."""
        return cls(
            id=str(item.get("id", "")),
            title=str(item.get("title", "")),
            audio_url=str(item.get("audioUrl") or item.get("audio_url", "")),
            image_url=str(item.get("imageUrl") or item.get("image_url", "")),
            image_large_url=str(item.get("imageUrl") or item.get("image_url", "")),
            status="",
        )


# ----- Payload para publicar no YouTube (enviado no Kafka) -----
class PublishToYouTubePayload(BaseModel):
    """Mensagem no tópico video-ready-for-youtube."""

    request_id: str = Field(default="", description="ID da solicitação original")
    title: str = Field(..., description="Título do vídeo no YouTube")
    description: str = Field(default="", description="Descrição do vídeo")
    video_path: str = Field(..., description="Caminho absoluto do arquivo de vídeo no disco")
    tags: list[str] = Field(default_factory=list, description="Tags para o YouTube")
    genre: str = Field(default="", description="Gênero (pode ser usado em tags)")
    # Canal: use credentials de outra conta. Caminho para credentials.json dessa conta (ex: ./credentials_canal_musica.json)
    youtube_credentials_path: str = Field(default="", description="Opcional: path do credentials.json da conta/canal desejado")
