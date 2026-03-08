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
            try:
                self._client = Suno(cookie=settings.suno_cookie, model_version=model)
            except Exception as e:
                msg = str(e)
                if "Session ID" in msg or "session" in msg.lower() or "SUNO_COOKIE" in msg:
                    raise ValueError(
                        "Cookie do Suno inválido ou expirado. Pegue um novo em app.suno.ai: "
                        "F12 → Aba Network → recarregue a página → procure a requisição com "
                        "'client?_clerk_js_version' → copie o header Cookie e atualize SUNO_COOKIE no .env. "
                        "Cookies do Suno expiram em ~7 dias."
                    ) from e
                raise
        return self._client

    def generate(self, request: GenerateMusicRequest) -> list[SunoSongInfo]:
        """Gera música no Suno a partir de título, letra e gênero."""
        client = self._get_client(request.model_version)
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
                    "A API não-oficial do Suno que esta biblioteca usa está suspensa no momento. "
                    "Tente atualizar o pacote: pip install -U SunoAI. "
                    "Ou use outra forma de gerar o áudio e alimentar o restante da pipeline (vídeo + YouTube)."
                ) from e
            if "Error response:" in msg and ("<html" in msg.lower() or "suspended" in msg.lower()):
                raise ValueError(
                    "Suno retornou erro (serviço suspenso ou indisponível). "
                    "A lib SunoAI usa uma API não-oficial que pode ter sido desativada. "
                    "Atualize o pacote ou aguarde atualização dos mantenedores."
                ) from e
            raise
        return [SunoSongInfo.from_clip(s) for s in songs]

    def download_audio(self, song: SunoSongInfo, output_dir: Path | None = None) -> Path:
        """Baixa o áudio de uma música Suno para output_dir. Retorna o path do arquivo."""
        client = self._get_client("chirp-v3-5")
        out = output_dir or settings.downloads_dir
        out.mkdir(parents=True, exist_ok=True)
        file_path = client.download(song=song.id, path=str(out))
        return Path(file_path)
