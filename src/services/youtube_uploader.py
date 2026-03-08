"""Upload de vídeos para o YouTube via Google API."""
from pathlib import Path
from typing import Optional

from src.config import settings
from src.models.schemas import PublishToYouTubePayload


class YouTubeUploader:
    """Faz upload de um arquivo de vídeo para o YouTube usando OAuth2."""

    def __init__(self) -> None:
        self._youtube = None

    def _get_youtube_client(self):
        if self._youtube is None:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload
            import os

            SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
            creds = None
            token_path = Path(settings.google_client_secrets_path).parent / "credentials.json"

            if token_path.exists():
                creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not settings.google_client_secrets_path or not Path(settings.google_client_secrets_path).exists():
                        raise FileNotFoundError(
                            f"Arquivo de credenciais não encontrado: {settings.google_client_secrets_path}. "
                            "Baixe client_secrets.json do Google Cloud Console."
                        )
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(settings.google_client_secrets_path), SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                with open(token_path, "w") as f:
                    f.write(creds.to_json())

            self._youtube = build("youtube", "v3", credentials=creds)
        return self._youtube

    def upload(self, payload: PublishToYouTubePayload) -> str:
        """
        Faz upload do vídeo para o YouTube.
        Retorna o ID do vídeo no YouTube.
        """
        from googleapiclient.http import MediaFileUpload

        youtube = self._get_youtube_client()
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
