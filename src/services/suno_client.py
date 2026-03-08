"""Cliente para gerar e baixar músicas: sunoapi.org (recomendado) ou lib SunoAI (cookie)."""
from pathlib import Path
from typing import Any

from src.config import settings
from src.models.schemas import GenerateMusicRequest, SunoSongInfo


def _use_sunoapi() -> bool:
    return bool(settings.sunoapi_key and settings.sunoapi_key.strip())


class SunoService:
    """
    Se SUNOAPI_KEY estiver definido, usa a API https://docs.sunoapi.org (api.sunoapi.org).
    Caso contrário, usa a lib SunoAI com SUNO_COOKIE.
    """

    def __init__(self) -> None:
        self._lib_client: Any = None
        self._sunoapi_client: Any = None

    def _get_sunoapi_client(self):
        if self._sunoapi_client is None:
            from src.services.suno_sunoapi import SunoAPIOrgClient
            self._sunoapi_client = SunoAPIOrgClient()
        return self._sunoapi_client

    def _get_lib_client(self, model_version: str = "chirp-v3-5") -> Any:
        if self._lib_client is None:
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
            try:
                self._lib_client = Suno(cookie=settings.suno_cookie, model_version=model)
            except Exception as e:
                msg = str(e)
                if "Session ID" in msg or "session" in msg.lower() or "SUNO_COOKIE" in msg:
                    raise ValueError(
                        "Cookie do Suno inválido ou expirado. Use SUNOAPI_KEY (sunoapi.org) ou atualize SUNO_COOKIE."
                    ) from e
                raise
        return self._lib_client

    def generate(self, request: GenerateMusicRequest) -> list[SunoSongInfo]:
        """Gera música (via sunoapi.org ou lib SunoAI)."""
        if _use_sunoapi():
            return self._get_sunoapi_client().generate(request)
        client = self._get_lib_client(request.model_version)
        tags = request.genre or "music"
        try:
            songs = client.generate(
                prompt=request.lyrics,
                is_custom=True,
                tags=tags,
                title=request.title,
                make_instrumental=request.make_instrumental,
                wait_audio=True,
                model_version=request.model_version,
            )
        except Exception as e:
            msg = str(e)
            if "Service Suspended" in msg or "service has been suspended" in msg.lower():
                raise ValueError(
                    "A API da lib SunoAI está suspensa. Configure SUNOAPI_KEY (https://sunoapi.org/api-key) para usar a API sunoapi.org."
                ) from e
            if "Error response:" in msg and ("<html" in msg.lower() or "suspended" in msg.lower()):
                raise ValueError(
                    "Suno retornou erro. Configure SUNOAPI_KEY para usar a API sunoapi.org."
                ) from e
            raise
        return [SunoSongInfo.from_clip(s) for s in songs]

    def download_audio(self, song: SunoSongInfo, output_dir: Path | None = None) -> Path:
        """Baixa o áudio (via sunoapi.org ou lib)."""
        if _use_sunoapi():
            return self._get_sunoapi_client().download_audio(song, output_dir)
        client = self._get_lib_client("chirp-v3-5")
        out = output_dir or settings.downloads_dir
        out.mkdir(parents=True, exist_ok=True)
        file_path = client.download(song=song.id, path=str(out))
        return Path(file_path)
