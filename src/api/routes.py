"""Rotas da API: gerar música (síncrono ou enfileirar no Kafka) e enfileirar publicação."""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)

from src.api.dependencies import verify_api_key
from src.config import settings
from src.models.schemas import GenerateMusicRequest, SunoSongInfo

router = APIRouter(prefix="/api", tags=["api"])


@router.post("/generate")
async def generate_music(
    body: GenerateMusicRequest,
    _: str = Depends(verify_api_key),
):
    """
    Gera música no Suno (título, letra, gênero), monta o vídeo e envia para a fila
    de publicação no YouTube. Retorna os dados da música gerada e o request_id.
    """
    from src.kafka.producer import get_producer, send_publish_message
    from src.services.suno_client import SunoService
    from src.services.video_builder import VideoBuilder

    request_id = str(uuid.uuid4())
    try:
        suno = SunoService()
        songs = suno.generate(body)
        if not songs:
            raise HTTPException(status_code=502, detail="Suno não retornou músicas")

        song = songs[0]
        audio_path = suno.download_audio(song)

        builder = VideoBuilder()
        output_dir = settings.output_videos_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        video_path = builder.build(
            audio_path=audio_path,
            song=song,
            title=body.title,
            output_path=output_dir / f"{request_id}.mp4",
        )

        payload = {
            "request_id": request_id,
            "title": body.title,
            "description": f"Música: {body.title}\nGênero: {body.genre}",
            "video_path": str(video_path.resolve()),
            "tags": [t.strip() for t in body.genre.split(",") if t.strip()] if body.genre else [],
            "genre": body.genre,
        }
        producer = await get_producer()
        await send_publish_message(producer, payload)

        return {
            "request_id": request_id,
            "songs": [_song_to_dict(s) for s in songs],
            "video_path": str(video_path),
            "queued_for_youtube": True,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("POST /api/generate failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/queue")
async def generate_music_queue(
    body: GenerateMusicRequest,
    _: str = Depends(verify_api_key),
):
    """
    Apenas enfileira o pedido no Kafka (tópico music-generation-requests).
    Um worker consumer processa em background: Suno -> vídeo -> enfileira publicação.
    Retorna imediatamente com request_id.
    """
    from src.kafka.producer import get_producer, send_generate_message

    request_id = str(uuid.uuid4())
    payload = {
        "request_id": request_id,
        "title": body.title,
        "lyrics": body.lyrics,
        "genre": body.genre,
        "make_instrumental": body.make_instrumental,
        "model_version": body.model_version,
    }
    try:
        producer = await get_producer()
        await send_generate_message(producer, payload)
        return {"request_id": request_id, "queued": True, "message": "Pedido enfileirado para processamento."}
    except Exception as e:
        logger.exception("POST /api/generate/queue failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


def _song_to_dict(s: SunoSongInfo) -> dict:
    return {
        "id": s.id,
        "title": s.title,
        "audio_url": s.audio_url,
        "image_url": s.image_url,
    }
