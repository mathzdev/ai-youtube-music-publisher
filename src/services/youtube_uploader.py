"""Upload de vídeos para o YouTube via Google API."""
from pathlib import Path
from typing import Optional

from src.config import settings
from src.models.schemas import PublishToYouTubePayload


def _resolve_credentials_path(override: str = "") -> Path:
    """Path do arquivo credentials (token OAuth). Override vazio = default."""
    if override and override.strip():
        return Path(override.strip()).resolve()
    if getattr(settings, "youtube_credentials_path", "") and str(settings.youtube_credentials_path).strip():
        return Path(settings.youtube_credentials_path).resolve()
    return Path(settings.google_client_secrets_path).parent / "credentials.json"


class YouTubeUploader:
    """
    Upload para o YouTube. O canal é sempre o da conta do credentials usado.
    Para vários canais: use credentials diferentes (um arquivo por conta/canal).
    """

    def __init__(self) -> None:
        self._clients: dict[str, object] = {}  # path -> youtube client

    def _get_youtube_client(self, credentials_path: Optional[Path] = None) -> object:
        path = credentials_path or _resolve_credentials_path()
        path_str = str(path)
        if path_str in self._clients:
            return self._clients[path_str]

        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
        creds = None
        if path.exists():
            creds = Credentials.from_authorized_user_file(str(path), SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                secrets = settings.google_client_secrets_path
                if not secrets or not Path(secrets).exists():
                    raise FileNotFoundError(
                        f"Arquivo de credenciais não encontrado: {secrets}. "
                        "Baixe client_secrets.json do Google Cloud Console."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(str(secrets), SCOPES)
                creds = flow.run_local_server(port=0)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                f.write(creds.to_json())

        self._clients[path_str] = build("youtube", "v3", credentials=creds)
        return self._clients[path_str]

    def upload(self, payload: PublishToYouTubePayload) -> str:
        """
        Faz upload do vídeo para o YouTube.
        Retorna o ID do vídeo no YouTube.
        """
        from googleapiclient.http import MediaFileUpload

        creds_path = _resolve_credentials_path(payload.youtube_credentials_path) if (getattr(payload, "youtube_credentials_path", None) or "").strip() else None
        youtube = self._get_youtube_client(creds_path)
        video_path = Path(payload.video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Vídeo não encontrado: {video_path}")

        body = {
            "snippet": {
                "title": payload.title[:100],
                "description": payload.description or "",
                "tags": payload.tags or [],
                "categoryId": settings.youtube_category_id,
            },
            "status": {
                "privacyStatus": settings.youtube_privacy_status,
            },
        }

        media = MediaFileUpload(
            str(video_path),
            mimetype="video/mp4",
            resumable=True,
            chunksize=1024 * 1024,
        )

        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
        return response["id"]
