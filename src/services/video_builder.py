"""Monta vídeo a partir de áudio + imagem de capa + título (fundo preto com texto)."""
from pathlib import Path
from typing import Optional

import requests
from PIL import Image, ImageDraw, ImageFont

try:
    from moviepy import AudioFileClip, ImageClip, CompositeVideoClip, ColorClip
except ImportError:
    from moviepy.editor import AudioFileClip, ImageClip, CompositeVideoClip, ColorClip

from src.config import settings
from src.models.schemas import SunoSongInfo


def _download_image(url: str, dest: Path) -> Path:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(resp.content)
    return dest


class VideoBuilder:
    """Gera um vídeo MP4: fundo preto, título no topo, imagem Suno centralizada, áudio da música."""

    def __init__(self, work_dir: Optional[Path] = None) -> None:
        self.work_dir = work_dir or settings.work_dir
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def build(
        self,
        audio_path: Path,
        song: SunoSongInfo,
        title: str,
        output_path: Optional[Path] = None,
        width: int = 1920,
        height: int = 1080,
    ) -> Path:
        """
        Cria vídeo: fundo preto, título em texto no topo, imagem da capa Suno no centro, áudio.
        Retorna o path do arquivo de vídeo gerado.
        """
        output_path = output_path or self.work_dir / f"{song.id}.mp4"
        output_path = Path(output_path).resolve()

        # Duração do áudio
        audio_clip = AudioFileClip(str(audio_path))
        duration = audio_clip.duration

        # Baixar imagem de capa
        image_url = song.image_large_url or song.image_url
        if not image_url:
            raise ValueError("Suno song sem image_url/image_large_url")
        image_file = self.work_dir / f"{song.id}_cover.png"
        _download_image(image_url, image_file)

        # Clipe de imagem (redimensionar para caber mantendo proporção)
        img_clip = ImageClip(str(image_file))
        img_w, img_h = img_clip.size
        scale = min((width * 0.6) / img_w, (height * 0.5) / img_h)
        new_w, new_h = int(img_w * scale), int(img_h * scale)
        # MoviePy 2.x usa resized(); 1.x usa resize()
        if hasattr(img_clip, "resized"):
            img_clip = img_clip.resized((new_w, new_h))
        else:
            img_clip = img_clip.resize((new_w, new_h))
        img_clip = img_clip.with_duration(duration)
        img_clip = img_clip.with_position(("center", height // 2 - new_h // 2))

        # Fundo preto
        bg = ColorClip(size=(width, height), color=(0, 0, 0)).with_duration(duration)

        # Título no topo (imagem PIL para não depender de ImageMagick)
        title_clip = self._make_title_clip(title, width, height, duration)
        if title_clip is not None:
            video = CompositeVideoClip([bg, img_clip, title_clip])
        else:
            video = CompositeVideoClip([bg, img_clip])
        video = video.with_audio(audio_clip)
        video = video.with_fps(30)

        video.write_videofile(
            str(output_path),
            codec="libx264",
            audio_codec="aac",
            fps=30,
            logger=None,
        )

        audio_clip.close()
        img_clip.close()
        bg.close()
        if title_clip is not None:
            title_clip.close()
        video.close()

        return output_path

    def _make_title_clip(
        self, title: str, width: int, height: int, duration: float
    ) -> Optional[ImageClip]:
        """Gera um clipe de título com PIL (sem ImageMagick)."""
        try:
            # Barra preta no topo com texto branco
            bar_height = 120
            img = Image.new("RGB", (width, bar_height), (0, 0, 0))
            draw = ImageDraw.Draw(img)
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 42)
            except OSError:
                try:
                    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 42)
                except OSError:
                    font = ImageFont.load_default()
            text = title[:60] + "..." if len(title) > 60 else title
            if hasattr(draw, "textbbox"):
                bbox = draw.textbbox((0, 0), text, font=font)
            else:
                bbox = draw.getbbox(text, font=font) or (0, 0, 10, 10)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            x = (width - tw) // 2
            y = (bar_height - th) // 2
            draw.text((x, y), text, fill="white", font=font)
            path = self.work_dir / "_title_bar.png"
            img.save(str(path))
            clip = ImageClip(str(path)).with_duration(duration).with_position((0, 0))
            return clip
        except Exception:
            return None
