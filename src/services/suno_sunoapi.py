"""
Cliente para a API https://docs.sunoapi.org (api.sunoapi.org).
Autenticação: Bearer token (API Key de https://sunoapi.org/api-key).
"""
import logging
import time
from pathlib import Path
from typing import Any

import requests

from src.config import settings
from src.models.schemas import GenerateMusicRequest, SunoSongInfo

logger = logging.getLogger(__name__)

# Limites por modelo (doc): prompt 3k (V4) / 5k (V4_5+), style 200/1k, title 80/100
MODEL_MAP = {
    "chirp-v3-5": "V4_5ALL",
    "chirp-v3-0": "V4_5",
    "chirp-v2-0": "V4",
}
DEFAULT_MODEL = "V4_5ALL"

POLL_INTERVAL = 12
POLL_TIMEOUT = 360  # 6 min

# Status de sucesso final (doc get-music-generation-details)
STATUS_SUCCESS = "SUCCESS"
STATUS_IN_PROGRESS = {"PENDING", "TEXT_SUCCESS", "FIRST_SUCCESS"}
STATUS_ERROR = {
    "SENSITIVE_WORD_ERROR",
    "CALLBACK_EXCEPTION",
    "GENERATE_AUDIO_FAILED",
    "CREATE_TASK_FAILED",
}


class SunoAPIOrgClient:
    """Cliente para api.sunoapi.org: POST generate + polling em record-info."""

    def __init__(self) -> None:
        self._session = requests.Session()
        base = (settings.sunoapi_base_url or "").rstrip("/")
        if not base:
            base = "https://api.sunoapi.org"
        self._base = base
        key = settings.sunoapi_key or ""
        if not key:
            raise ValueError(
                "SUNOAPI_KEY não configurado. Obtenha em https://sunoapi.org/api-key"
            )
        self._session.headers["Authorization"] = f"Bearer {key}"
        self._session.headers["Content-Type"] = "application/json"

    def generate(self, request: GenerateMusicRequest) -> list[SunoSongInfo]:
        """Envia tarefa de geração e faz polling até completar."""
        model = MODEL_MAP.get(request.model_version, DEFAULT_MODEL)
        style = (request.genre or "music").strip()[:1000]
        title = request.title[:100]
        body: dict[str, Any] = {
            "customMode": True,
            "instrumental": request.make_instrumental,
            "model": model,
            "prompt": request.lyrics,
            "style": style,
            "title": title,
            # callBackUrl é obrigatório na spec; usamos polling, então URL placeholder
            "callBackUrl": "https://example.com/callback",
        }

        r = self._session.post(
            f"{self._base}/api/v1/generate",
            json=body,
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()
        if data.get("code") != 200:
            raise ValueError(
                data.get("msg", "Erro ao submeter geração") or str(data)
            )
        task_id = (data.get("data") or {}).get("taskId")
        if not task_id:
            raise ValueError("Resposta da API sem taskId")

        logger.info("sunoapi.org: taskId=%s, aguardando conclusão (polling)...", task_id)
        return self._poll_until_done(task_id)

    def _poll_until_done(self, task_id: str) -> list[SunoSongInfo]:
        started = time.monotonic()
        while True:
            if time.monotonic() - started > POLL_TIMEOUT:
                raise TimeoutError("Timeout aguardando geração na sunoapi.org")
            r = self._session.get(
                f"{self._base}/api/v1/generate/record-info",
                params={"taskId": task_id},
                timeout=30,
            )
            r.raise_for_status()
            data = r.json()
            if data.get("code") != 200:
                raise ValueError(
                    data.get("msg", "Erro ao consultar status") or str(data)
                )
            payload = data.get("data") or {}
            response = payload.get("response") or {}
            status = (payload.get("status") or response.get("status") or "").strip()

            if status == STATUS_SUCCESS:
                suno_data = response.get("sunoData") or []
                if not suno_data:
                    raise ValueError("API retornou SUCCESS mas sem sunoData")
                return [SunoSongInfo.from_sunoapi_item(item) for item in suno_data]

            if status in STATUS_ERROR:
                err_msg = payload.get("errorMessage") or response.get("errorMessage") or status
                raise ValueError(f"Geração falhou na API: {err_msg}")

            logger.debug("Status: %s, aguardando %ss...", status or "unknown", POLL_INTERVAL)
            time.sleep(POLL_INTERVAL)

    def download_audio(self, song: SunoSongInfo, output_dir: Path | None = None) -> Path:
        """Baixa o áudio pela URL retornada pela API."""
        out = output_dir or settings.downloads_dir
        out = Path(out)
        out.mkdir(parents=True, exist_ok=True)
        url = song.audio_url
        if not url:
            raise ValueError("Música sem audio_url")
        r = self._session.get(url, timeout=120)
        r.raise_for_status()
        path = out / f"{song.id}.mp3"
        path.write_bytes(r.content)
        return path
