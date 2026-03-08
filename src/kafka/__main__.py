"""Permite rodar: python -m src.kafka generate|publish"""
import sys
from src.kafka.consumer import run_consumer

if __name__ == "__main__":
    role = sys.argv[1] if len(sys.argv) > 1 else None
    if role not in ("generate", "publish"):
        print("Uso: python -m src.kafka <generate|publish>")
        sys.exit(1)
    run_consumer(role)
