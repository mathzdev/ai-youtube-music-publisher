"""Handlers que processam mensagens Kafka: gerar música+vídeo e publicar no YouTube."""
import json
import uuid
from pathlib import Path

from src.config import settings
from src.kafka.producer import build_publish_payload
from src.models.schemas import GenerateMusicRequest, PublishToYouTubePayload


async def handle_generate_request(message_value: bytes) -> dict | None:
    """
    Processa mensagem do tópico music-generation-requests:
    gera música no Suno, monta o vídeo e envia para video-ready-for-youtube.
    Retorna o payload enviado para publicação (ou None em caso de erro).
    """
    from src.kafka.producer import get_producer, send_publish_message
    from src.services.suno_client import SunoService
    from src.services.video_builder import VideoBuilder

    try:
        data = json.loads(message_value.decode("utf-8"))
        request = GenerateMusicRequest(
            title=data["title"],
            lyrics=data["lyrics"],
            genre=data.get("genre", ""),
            make_instrumental=data.get("make_instrumental", False),
            model_version=data.get("model_version", "chirp-v3-5"),
            youtube_credentials_path=data.get("youtube_credentials_path", ""),
        )
    except Exception as e:
        print(f"[handle_generate] Payload inválido: {e}")
        return None

    request_id = data.get("request_id") or str(uuid.uuid4())
    try:
        suno = SunoService()
        songs = suno.generate(request)
        if not songs:
            print("[handle_generate] Suno não retornou músicas")
            return None

        song = songs[0]
        audio_path = suno.download_audio(song)

        builder = VideoBuilder()
        output_dir = settings.output_videos_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        video_path = builder.build(
            audio_path=audio_path,
            song=song,
            title=request.title,
            output_path=output_dir / f"{request_id}.mp4",
        )

        tags_list = [t.strip() for t in request.genre.split(",") if t.strip()] if request.genre else []
        payload = build_publish_payload(
            request_id=request_id,
            title=request.title,
            video_path=str(video_path.resolve()),
            description=f"Música: {request.title}\nGênero: {request.genre}",
            tags=tags_list,
            genre=request.genre or "",
            youtube_credentials_path=(request.youtube_credentials_path or "").strip(),
        )
        producer = await get_producer()
        await send_publish_message(producer, payload)
        return payload
    except Exception as e:
        print(f"[handle_generate] Erro: {e}")
        return None


async def handle_publish_to_youtube(message_value: bytes) -> bool:
    """
    Processa mensagem do tópico video-ready-for-youtube: faz upload do vídeo para o YouTube.
    Retorna True se o upload foi iniciado com sucesso.
    """
    try:
        data = json.loads(message_value.decode("utf-8"))
        payload = PublishToYouTubePayload(
            request_id=data.get("request_id", ""),
            title=data["title"],
            description=data.get("description", ""),
            video_path=data["video_path"],
            tags=data.get("tags", []),
            genre=data.get("genre", ""),
            youtube_credentials_path=data.get("youtube_credentials_path", ""),
        )
    except Exception as e:
        print(f"[handle_publish] Payload inválido: {e}")
        return False

    video_path = Path(payload.video_path)
    print(f"[handle_publish] Iniciando upload: {payload.title}")
    print(f"  arquivo: {video_path}")
    if (getattr(payload, "youtube_credentials_path", None) or "").strip():
        print(f"  canal (credentials): {payload.youtube_credentials_path}")
    if not video_path.exists():
        print(f"[handle_publish] ERRO: Arquivo não encontrado: {video_path}")
        return False

    try:
        from src.services.youtube_uploader import YouTubeUploader

        uploader = YouTubeUploader()
        print(f"[handle_publish] Enviando para o YouTube...")
        video_id = uploader.upload(payload)
        url = f"https://www.youtube.com/watch?v={video_id}"
        print(f"[handle_publish] Vídeo publicado: {payload.title}")
        print(f"  → {url}")
        return True
    except FileNotFoundError as e:
        print(f"[handle_publish] Arquivo não encontrado: {e}")
        return False
    except Exception as e:
        print(f"[handle_publish] Erro no upload: {e}")
        import traceback
        traceback.print_exc()
        return False
