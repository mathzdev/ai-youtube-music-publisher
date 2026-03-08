"""Producer Kafka para enviar mensagens de publicação no YouTube."""
import json
from typing import Any

from aiokafka import AIOKafkaProducer

from src.config import settings

_producer: AIOKafkaProducer | None = None


def build_publish_payload(
    *,
    request_id: str,
    title: str,
    video_path: str,
    description: str = "",
    tags: list[str] | None = None,
    genre: str = "",
    youtube_credentials_path: str = "",
) -> dict[str, Any]:
    """
    Monta o payload enviado ao tópico video-ready-for-youtube.
    Usado pelo POST /api/generate e pelo script queue_video_for_youtube.py
    para garantir o mesmo formato que o consumer handle_publish_to_youtube espera.
    """
    return {
        "request_id": request_id,
        "title": title,
        "description": description or "",
        "video_path": video_path,
        "tags": list(tags) if tags is not None else [],
        "genre": genre or "",
        "youtube_credentials_path": (youtube_credentials_path or "").strip(),
    }


async def get_producer() -> AIOKafkaProducer:
    global _producer
    if _producer is None:
        _producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        await _producer.start()
    return _producer


async def send_publish_message(producer: AIOKafkaProducer, payload: dict[str, Any]) -> None:
    """Envia uma mensagem para o tópico video-ready-for-youtube."""
    await producer.send_and_wait(settings.kafka_topic_publish, value=payload)


async def send_generate_message(producer: AIOKafkaProducer, payload: dict[str, Any]) -> None:
    """Envia uma mensagem para o tópico music-generation-requests (para processamento assíncrono)."""
    await producer.send_and_wait(settings.kafka_topic_generate, value=payload)


async def stop_producer() -> None:
    global _producer
    if _producer is not None:
        await _producer.stop()
        _producer = None
