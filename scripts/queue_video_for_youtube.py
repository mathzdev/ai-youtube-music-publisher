#!/usr/bin/env python3
"""
Enfileira um vídeo já gerado no tópico Kafka video-ready-for-youtube
para o consumer de publicação fazer o upload no YouTube.

Uso (a partir da raiz do projeto):
  python scripts/queue_video_for_youtube.py output_videos/meu_video.mp4 "Título"
  python scripts/queue_video_for_youtube.py output_videos/meu_video.mp4 "Título" credentials_canal_musica.json

Canal: para publicar em outro canal, use outro arquivo de credentials (uma conta Google por canal).
Gere com: rode o consumer uma vez com YOUTUBE_CREDENTIALS_PATH=./creds_canal_b.json e autentique;
depois use esse path na mensagem ou no script.

Requisitos: Kafka rodando (docker compose up -d), variáveis KAFKA_* no .env.
"""
import asyncio
import sys
from pathlib import Path

# raiz do projeto no path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import settings
from src.kafka.producer import build_publish_payload, get_producer, send_publish_message, stop_producer


async def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: python scripts/queue_video_for_youtube.py <caminho_do_video> [titulo] [credentials_path]")
        print("Ex.: python scripts/queue_video_for_youtube.py output_videos/meu.mp4 \"Minha Música\"")
        print("     python scripts/queue_video_for_youtube.py output_videos/meu.mp4 \"Título\" credentials_canal_b.json")
        sys.exit(1)

    video_path = Path(sys.argv[1]).resolve()
    title = sys.argv[2] if len(sys.argv) > 2 else video_path.stem
    credentials_path = sys.argv[3].strip() if len(sys.argv) > 3 else ""

    if not video_path.exists():
        print(f"Erro: arquivo não encontrado: {video_path}")
        sys.exit(1)

    payload = build_publish_payload(
        request_id=video_path.stem,
        title=title,
        video_path=str(video_path),
        description=f"Vídeo: {title}",
        tags=[],
        genre="",
        youtube_credentials_path=credentials_path,
    )

    print(f"Kafka: {settings.kafka_bootstrap_servers}")
    print(f"Tópico: {settings.kafka_topic_publish}")
    print(f"Vídeo: {video_path} ({video_path.stat().st_size // 1024} KB)")
    print(f"Título: {title}")
    if credentials_path:
        print(f"Canal (credentials): {credentials_path}")
    print("Enviando mensagem...")

    try:
        producer = await get_producer()
        await send_publish_message(producer, payload)
        print("OK. Mensagem enfileirada. Rode o consumer para publicar no YouTube:")
        print("  python -m src.kafka publish")
    except Exception as e:
        print(f"Erro ao enviar para o Kafka: {e}")
        sys.exit(1)
    finally:
        await stop_producer()


if __name__ == "__main__":
    asyncio.run(main())
