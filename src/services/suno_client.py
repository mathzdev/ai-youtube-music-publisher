"""Cliente para gerar e baixar músicas via Suno AI."""
from pathlib import Path
from typing import Any

from src.config import settings
from src.models.schemas import GenerateMusicRequest, SunoSongInfo


class SunoService:
    """Serviço que encapsula a biblioteca SunoAI."""

    def __init__(self) -> None:
        self._client: Any = None

    def _get_client(self, model_version: str = "chirp-v3-5") -> Any:
        if self._client is None:
            try:
                from suno import Suno, ModelVersions
            except ImportError as e:
                raise RuntimeError(
                    "Instale o pacote SunoAI: pip install SunoAI"
                ) from e
            if not settings.suno_cookie:
                raise ValueError("SUNO_COOKIE não configurado no ambiente")
            model_map = {
                "chirp-v3-5": ModelVersions.CHIRP_V3_5,
                "chirp-v3-0": ModelVersions.CHIRP_V3_0,
                "chirp-v2-0": ModelVersions.CHIRP_V2_0,
            }
            model = model_map.get(model_version, ModelVersions.CHIRP_V3_5)
            self._client = Suno(cookie=settings.suno_cookie, model_version=model)
        return self._client

    def generate(self, request: GenerateMusicRequest) -> list[SunoSongInfo]:
        """Gera música no Suno a partir de título, letra e gênero."""
        client = self._get_client(request.model_version)
        tags = request.genre or "music"
        songs = client.generate(
            prompt=request.lyrics,
            is_custom=True,
            tags=tags,
            title=request.title,
            make_instrumental=request.make_instrumental,
            wait_audio=True,
            model_version=request.model_version,
        )
        return [SunoSongInfo.from_clip(s) for s in songs]

    def download_audio(self, song: SunoSongInfo, output_dir: Path | None = None) -> Path:
        """Baixa o áudio de uma música Suno para output_dir. Retorna o path do arquivo."""
        client = self._get_client("chirp-v3-5")
        out = output_dir or settings.downloads_dir
        out.mkdir(parents=True, exist_ok=True)
        file_path = client.download(song=song.id, path=str(out))
        return Path(file_path)
