"""Producer Kafka para enviar mensagens de publicação no YouTube."""
import json
from typing import Any

from aiokafka import AIOKafkaProducer

from src.config import settings

_producer: AIOKafkaProducer | None = None


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
