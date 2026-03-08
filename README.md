# AI YouTube Music Publisher

Pipeline em Python para **gerar músicas com Suno AI**, montar vídeos (capa + título + áudio) e **publicar no YouTube**, via API (API key) ou fila **Kafka**.

## Workflow

1. **Entrada**: API `POST /api/generate` (com `X-API-Key`) ou mensagem no tópico Kafka `music-generation-requests` com: `title`, `lyrics`, `genre`.
2. **Suno**: Geração da música (SunoAI) e download do áudio + imagem de capa.
3. **Vídeo**: Montagem do vídeo (fundo preto, título no topo, imagem Suno, áudio) com MoviePy.
4. **Publicação**: Mensagem no tópico `video-ready-for-youtube` é consumida por um worker que faz upload para o YouTube (Google API).

## Pré-requisitos

- Python 3.10+
- Cookie do Suno (obter em [suno.ai](https://suno.ai) → DevTools → Network → cookie `_clerk_js_version` ou similar)
- Conta Google Cloud com YouTube Data API v3 e arquivo `client_secrets.json` (OAuth 2.0)
- Kafka (local ou remoto) para o fluxo assíncrono

## Instalação

```bash
cd ai-youtube-music-publisher
python -m venv .venv
source .venv/bin/activate   # ou .venv\Scripts\activate no Windows
pip install -r requirements.txt
cp .env.example .env
# Edite .env: SUNO_COOKIE, API_KEY, e opcionalmente Kafka e paths.
```

## Variáveis de ambiente (.env)

| Variável | Descrição |
|----------|-----------|
| `SUNO_COOKIE` | Cookie de autenticação do Suno (obrigatório para gerar músicas) |
| `API_KEY` | Chave para proteger `POST /api/generate` (header `X-API-Key`) |
| `KAFKA_BOOTSTRAP_SERVERS` | Ex.: `localhost:9092` |
| `KAFKA_TOPIC_GENERATE` | Tópico de pedidos de geração (default: `music-generation-requests`) |
| `KAFKA_TOPIC_PUBLISH` | Tópico de vídeos prontos para YouTube (default: `video-ready-for-youtube`) |
| `GOOGLE_CLIENT_SECRETS_PATH` | Caminho para `client_secrets.json` do Google |
| `YOUTUBE_CATEGORY_ID` | Categoria do vídeo (10 = Música) |
| `YOUTUBE_PRIVACY_STATUS` | `private`, `unlisted` ou `public` |

## Uso

### 1. Subir o Kafka (opcional, para fluxo assíncrono)

```bash
docker compose up -d
```

### 2. Rodar a API

```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Gerar música e enfileirar publicação (síncrono)

Gera no Suno, monta o vídeo e envia para a fila de publicação no YouTube:

```bash
curl -X POST http://localhost:8000/api/generate \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Minha Música",
    "lyrics": "Primeira linha da letra\nSegunda linha...",
    "genre": "pop, male voice"
  }'
```

### 4. Apenas enfileirar no Kafka (assíncrono)

Só envia o pedido para o Kafka; um worker processa em background:

```bash
curl -X POST http://localhost:8000/api/generate/queue \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Outra Música",
    "lyrics": "Letra aqui...",
    "genre": "rock"
  }'
```

Para processar essas mensagens, rode o **consumer de geração** (Suno + vídeo + envia para fila de publicação):

```bash
python -m src.kafka generate
```

### 5. Publicar no YouTube

O consumer de publicação lê o tópico `video-ready-for-youtube` e faz o upload:

```bash
python -m src.kafka publish
```

Na primeira execução, o Google abre o navegador para você autorizar o app; as credenciais são salvas em `credentials.json`.

## Estrutura do projeto

```
src/
  main.py              # App FastAPI
  config.py            # Settings (env)
  api/
    routes.py          # POST /api/generate e /api/generate/queue
    dependencies.py    # Validação X-API-Key
  models/
    schemas.py         # GenerateMusicRequest, PublishToYouTubePayload, SunoSongInfo
  services/
    suno_client.py     # Suno: generate + download
    video_builder.py   # MoviePy: imagem + áudio + título -> MP4
    youtube_uploader.py # Google API: upload do vídeo
  kafka/
    producer.py        # Enviar para topic_generate e topic_publish
    consumer.py        # Consumers: generate e publish
    handlers.py        # Lógica: Suno -> vídeo -> Kafka; Kafka -> YouTube
```

## Tópicos Kafka

- **music-generation-requests**: payload `{ "request_id", "title", "lyrics", "genre", "make_instrumental", "model_version" }`. O consumer gera a música, monta o vídeo e envia para `video-ready-for-youtube`.
- **video-ready-for-youtube**: payload `{ "request_id", "title", "description", "video_path", "tags", "genre" }`. O consumer faz upload do arquivo `video_path` para o YouTube.

## YouTube API

1. Crie um projeto no [Google Cloud Console](https://console.cloud.google.com).
2. Ative a **YouTube Data API v3**.
3. Crie credenciais **OAuth 2.0** (tipo “Aplicativo para computador”) e baixe o JSON.
4. Salve como `client_secrets.json` na raiz do projeto (ou ajuste `GOOGLE_CLIENT_SECRETS_PATH`).

## Licença

MIT.
