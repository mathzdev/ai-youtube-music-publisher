"""Consumers Kafka: processar pedidos de geração e publicar no YouTube."""
import asyncio
import json

from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError

from src.config import settings
from src.kafka.handlers import handle_generate_request, handle_publish_to_youtube


async def run_generate_consumer() -> None:
    """
    Consome o tópico music-generation-requests: para cada mensagem,
    gera música no Suno, monta o vídeo e envia para video-ready-for-youtube.
    """
    consumer = AIOKafkaConsumer(
        settings.kafka_topic_generate,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id="music-generation-workers",
        value_deserializer=lambda x: x,
    )
    await consumer.start()
    try:
        async for msg in consumer:
            try:
                await handle_generate_request(msg.value)
            except Exception as e:
                print(f"[generate_consumer] Erro ao processar mensagem: {e}")
    finally:
        await consumer.stop()


async def run_publish_consumer() -> None:
    """
    Consome o tópico video-ready-for-youtube e faz upload de cada vídeo para o YouTube.
    """
    consumer = AIOKafkaConsumer(
        settings.kafka_topic_publish,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id="youtube-publishers",
        value_deserializer=lambda x: x,
    )
    await consumer.start()
    try:
        async for msg in consumer:
            try:
                await handle_publish_to_youtube(msg.value)
            except Exception as e:
                print(f"[publish_consumer] Erro ao processar mensagem: {e}")
    finally:
        await consumer.stop()


def run_consumer(role: str) -> None:
    """Entrypoint para rodar um consumer (role = 'generate' ou 'publish')."""
    if role == "generate":
        asyncio.run(run_generate_consumer())
    elif role == "publish":
        asyncio.run(run_publish_consumer())
    else:
        raise ValueError("role deve ser 'generate' ou 'publish'")
