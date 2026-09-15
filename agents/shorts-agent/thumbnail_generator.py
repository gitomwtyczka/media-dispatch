"""
agents/shorts-agent/thumbnail_generator.py

Automatyczne generowanie miniaturek (thumbnails) dla YouTube Shorts.

Pipeline:
  1. FLUX.1 Schnell (Fal.ai) → fotorealistyczne tło 1080x1920 BEZ tekstu
  2. Pillow → nakładanie hook tekstu (Nimbus Sans Narrow Bold, żółty neon + czarny obrys)
  3. Pillow → nakładanie branding overlay (01-overlay-staly.png) + rotacyjne CTA
  4. FFmpeg → baked-in first frame (0.5s na początku wideo)
  5. YouTube API thumbnails.set (try/catch — niestabilne dla Shorts, nie blokuje pipeline)

Wymagania:
  pip install fal-client Pillow
  ffmpeg w PATH

Konfiguracja:
  FAL_KEY — klucz API Fal.ai (https://fal.ai/dashboard)
  BRANDING_KIT_PATH — ścieżka do folderu prawy-shorts-kit
  SHORTS_OUTPUT_DIR — folder wynikowy (domyślnie: C:\\VSE\\Shorts\\thumbnails\\)
"""

import os
import re
import json
import base64
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, Tuple

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
except ImportError:
    raise ImportError("Wymagane: pip install Pillow")

try:
    import fal_client
except ImportError:
    raise ImportError("Wymagane: pip install fal-client")

# ============================================================
# KONFIGURACJA
# ============================================================

BRANDING_KIT_PATH = Path(
    os.getenv("BRANDING_KIT_PATH",
    r"D:\Biblioteki\prawy video\!_shortsy identyfikacja 9x16\prawy-shorts-kit")
)
FONT_PATH = BRANDING_KIT_PATH / "fonty" / "NimbusSansNarrow-Bold.otf"
OVERLAY_STATIC = BRANDING_KIT_PATH / "01-overlay-staly.png"
CTA_FILES = [
    BRANDING_KIT_PATH / "02-cta-subskrybuj.png",
    BRANDING_KIT_PATH / "03-cta-lapka.png",
    BRANDING_KIT_PATH / "04-cta-prawypl.png",
    BRANDING_KIT_PATH / "05-cta-udostepnij.png",
]
OUTPUT_DIR = Path(os.getenv("SHORTS_OUTPUT_DIR", r"C:\VSE\Shorts\thumbnails"))

# YouTube Shorts format
W, H = 1080, 1920

# Golden Box — strefa tekstu hook
HOOK_Y_CENTER = 480  # środek pionowo w zakresie 350-650px
HOOK_X_MIN = 100
HOOK_X_MAX = 850

# Kolory
COLOR_HOOK = "#FFE600"        # Żółty neon (hook text)
COLOR_STROKE = "#000000"      # czarny obrys
COLOR_RED = "#E21837"         # akcent Prawy.pl
COLOR_NAVY = "#07152B"        # tło Prawy.pl

HOOK_FONT_SIZE = 88
HOOK_STROKE_WIDTH = 10


# ============================================================
# GENEROWANIE TŁA (FLUX.1 Schnell via Fal.ai)
# ============================================================

NEGATIVE_PROMPT = (
    "text, words, letters, watermark, logo, subtitle, caption, "
    "low quality, blurry, distorted face, cartoon, anime, "
    "painting, illustration, drawing"
)


def generate_background(
    visual_prompt: str,
    fal_key: Optional[str] = None,
    output_path: Optional[Path] = None
) -> Path:
    """
    Generuje fotorealistyczne tło 1080x1920 przez FLUX.1 Schnell.
    BEZ tekstu, BEZ logo — tylko czyste tło.

    Args:
        visual_prompt: Opis sceny (po angielsku, bez tekstu!)
        fal_key: Klucz API Fal.ai (lub env FAL_KEY)
        output_path: Gdzie zapisać obraz (PNG)

    Returns:
        Path do zapisanego obrazu tła
    """
    key = fal_key or os.getenv("FAL_KEY")
    if not key:
        raise RuntimeError("Brak FAL_KEY. Ustaw zmienną środowiskową FAL_KEY lub podaj fal_key=")

    os.environ["FAL_KEY"] = key

    # Wymuszenie pionowego formatu 9:16, brak tekstu
    full_prompt = (
        f"{visual_prompt.strip()}, "
        "vertical 9:16 framing, cinematic, photorealistic, 8k, "
        "dramatic lighting, no text, no words, clean background"
    )

    result = fal_client.run(
        "fal-ai/flux/schnell",
        arguments={
            "prompt": full_prompt,
            "negative_prompt": NEGATIVE_PROMPT,
            "image_size": "portrait_4_3",  # najblizszy pionowy format
            "num_inference_steps": 4,
            "num_images": 1,
        }
    )

    image_url = result["images"][0]["url"]

    import requests
    img_data = requests.get(image_url, timeout=30).content

    if output_path is None:
        output_path = Path(tempfile.mktemp(suffix="_bg.png"))

    with open(output_path, "wb") as f:
        f.write(img_data)

    # Przeskaluj do dokładnie 1080x1920
    img = Image.open(output_path).convert("RGBA")
    img = img.resize((W, H), Image.Resampling.LANCZOS)
    img.save(output_path, "PNG")

    return output_path


# ============================================================
# OVERLAY TEKSTU (Pillow)
# ============================================================

def wrap_hook_text(text: str, max_chars_per_line: int = 16) -> list[str]:
    """Dzieli długi hook na 2 linie jeśli potrzeba."""
    words = text.upper().split()
    lines = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 <= max_chars_per_line:
            current = (current + " " + word).strip()
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines[:2]  # max 2 linie


def render_hook_text(
    bg_image: Image.Image,
    hook_text: str,
    font_path: Path = FONT_PATH,
    font_size: int = HOOK_FONT_SIZE,
) -> Image.Image:
    """
    Nakłada hook tekstu na tło.
    Żółty neon + gruby czarny obrys. Tekst wycentrowany w Golden Box (y~480px).
    """
    img = bg_image.copy().convert("RGBA")
    draw = ImageDraw.Draw(img)

    # Gradient ciemnieńicy za textem (kontrast)
    gradient = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    grad_draw = ImageDraw.Draw(gradient)
    for y in range(280, 700):
        alpha = int(120 * (1 - abs(y - 490) / 210))
        grad_draw.line([(0, y), (W, y)], fill=(0, 0, 0, max(0, min(alpha, 160))))
    img = Image.alpha_composite(img, gradient)
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype(str(font_path), size=font_size)
    except Exception:
        font = ImageFont.load_default()

    lines = wrap_hook_text(hook_text)
    total_height = len(lines) * (font_size + 12)
    start_y = HOOK_Y_CENTER - total_height // 2

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        text_x = (W - text_w) // 2
        text_y = start_y + i * (font_size + 12)

        # Czarny obrys
        draw.text(
            (text_x, text_y), line, font=font,
            fill=COLOR_HOOK,
            stroke_width=HOOK_STROKE_WIDTH,
            stroke_fill=COLOR_STROKE
        )

    return img


def apply_overlay(base: Image.Image, overlay_path: Path) -> Image.Image:
    """Nakłada plik PNG z alpha na base image (pozycja 0,0 — full 1080x1920)."""
    if not overlay_path.exists():
        print(f"[WARN] Brak overlaya: {overlay_path}")
        return base
    overlay = Image.open(overlay_path).convert("RGBA")
    overlay = overlay.resize((W, H), Image.Resampling.LANCZOS)
    base = base.convert("RGBA")
    return Image.alpha_composite(base, overlay)


# ============================================================
# TWORZENIE THUMBNAILS
# ============================================================

def create_thumbnail(
    hook_text: str,
    visual_prompt: str,
    short_id: str,
    cta_index: Optional[int] = None,
    fal_key: Optional[str] = None,
    bg_image_path: Optional[Path] = None,
) -> Path:
    """
    Tworzy pełną miniaturkę shorts:
    1. Tło (z Fal.ai lub z pliku)
    2. Hook tekst (Pillow)
    3. Stały overlay Prawy.pl (01-overlay-staly.png)
    4. Rotacyjne CTA (opcjonalnie)
    5. Zapis jako JPEG <2MB

    Args:
        hook_text: Krotki hasło (2-4 słowa), np. "SKANDAL W SEJMIE!"
        visual_prompt: Opis sceny dla FLUX (po angielsku)
        short_id: YouTube Video ID (do nazwy pliku)
        cta_index: Indeks CTA 0-3 (None = bez CTA)
        fal_key: Klucz Fal.ai
        bg_image_path: Opcjonalnie gotowe tło (pomija Fal.ai)

    Returns:
        Path do pliku thumbnail.jpg
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{short_id}_thumbnail.jpg"

    # 1. Tło
    if bg_image_path and bg_image_path.exists():
        bg = Image.open(bg_image_path).convert("RGBA")
        bg = bg.resize((W, H), Image.Resampling.LANCZOS)
    else:
        tmp_bg = OUTPUT_DIR / f"{short_id}_bg.png"
        generate_background(visual_prompt, fal_key=fal_key, output_path=tmp_bg)
        bg = Image.open(tmp_bg).convert("RGBA")

    # 2. Hook tekst
    img = render_hook_text(bg, hook_text)

    # 3. Stały overlay (badge Prawy.pl Shorts)
    img = apply_overlay(img, OVERLAY_STATIC)

    # 4. Rotacyjne CTA
    if cta_index is not None and 0 <= cta_index < len(CTA_FILES):
        img = apply_overlay(img, CTA_FILES[cta_index])

    # 5. Zapis JPEG
    img.convert("RGB").save(out_path, "JPEG", quality=90)
    print(f"[OK] Thumbnail zapisany: {out_path}")
    return out_path


# ============================================================
# BAKED-IN FIRST FRAME (FFmpeg)
# ============================================================

def bake_thumbnail_into_video(
    video_path: Path,
    thumbnail_path: Path,
    output_path: Optional[Path] = None,
    frame_duration: float = 0.5,
) -> Path:
    """
    Wkleja thumbnail jako pierwsze {frame_duration}s wideo.
    Metoda: thumbnail jako statyczny klip → concat z oryginałem.

    Args:
        video_path: Wejściowe wideo (mp4)
        thumbnail_path: Miniaturka JPEG 1080x1920
        output_path: Plik wyjściowy (mp4)
        frame_duration: Czas trwania pierwszej klatki (s)

    Returns:
        Path do wideo z wbudowaną miniaturką
    """
    if output_path is None:
        stem = video_path.stem
        output_path = video_path.parent / f"{stem}_with_thumbnail.mp4"

    # Pobierz framerate z oryginalnego wideo
    probe_cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", str(video_path)
    ]
    probe = subprocess.run(probe_cmd, capture_output=True, text=True)
    fps = "30"  # default
    try:
        streams = json.loads(probe.stdout).get("streams", [])
        for s in streams:
            if s.get("codec_type") == "video":
                r = s.get("r_frame_rate", "30/1")
                num, den = r.split("/")
                fps = str(round(int(num) / int(den)))
                break
    except Exception:
        pass

    # FFmpeg: thumbnail (loop 0.5s) + oryginalł concat
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-t", str(frame_duration),
        "-i", str(thumbnail_path),
        "-i", str(video_path),
        "-filter_complex",
        f"[0:v]scale={W}:{H},setsar=1,fps={fps}[thumb];"
        f"[1:v]scale={W}:{H},setsar=1[vid];"
        f"[thumb][vid]concat=n=2:v=1:a=0[outv];"
        f"[1:a]apad[outa]",
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-c:a", "aac",
        "-shortest",
        str(output_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg error: {result.stderr[-500:]}")

    print(f"[OK] Wideo z thumbnail: {output_path}")
    return output_path


# ============================================================
# YOUTUBE API thumbnails.set (try/catch — niestabilne dla Shorts)
# ============================================================

def upload_thumbnail_to_youtube(
    video_id: str,
    thumbnail_path: Path,
    oauth_token: str,
) -> dict:
    """
    Próbuje ustawić miniaturkę przez YouTube Data API.
    Dla Shorts może być niestabilne (Google Won't Fix).
    Zawsze zapisuje plik lokalnie — nie blokuje pipeline'u przy błędzie.
    """
    import requests

    url = f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId={video_id}"
    headers = {
        "Authorization": f"Bearer {oauth_token}",
        "Content-Type": "image/jpeg",
    }
    try:
        with open(thumbnail_path, "rb") as f:
            resp = requests.post(url, headers=headers, data=f, timeout=30)
        if resp.status_code == 200:
            return {"status": "ok", "video_id": video_id}
        else:
            return {"status": "api_error", "code": resp.status_code, "body": resp.text[:200]}
    except Exception as e:
        return {"status": "exception", "error": str(e)}


# ============================================================
# FULL PIPELINE
# ============================================================

def generate_short_thumbnail(
    short_id: str,
    hook_text: str,
    visual_prompt: str,
    cta_index: Optional[int] = None,
    video_path: Optional[Path] = None,
    oauth_token: Optional[str] = None,
    fal_key: Optional[str] = None,
) -> dict:
    """
    Pełny pipeline thumbnail dla jednego shorta.

    Args:
        short_id: YouTube Video ID
        hook_text: Krotkie hasło (2-4 słowa), np. "KOMISJA MARTWA?"
        visual_prompt: Scena dla FLUX (po angielsku, bez tekstu)
        cta_index: 0=subskrybuj, 1=łapka, 2=prawypl, 3=udostepnij, None=brak
        video_path: Ścieżka do pliku MP4 (dla baked-in frame)
        oauth_token: Token YouTube (dla thumbnails.set)
        fal_key: Klucz Fal.ai

    Returns:
        dict ze statusami każdego etapu
    """
    result = {
        "short_id": short_id,
        "hook_text": hook_text,
        "thumbnail_path": None,
        "baked_video_path": None,
        "yt_thumbnail_status": None,
    }

    # 1. Generuj thumbnail
    try:
        thumb_path = create_thumbnail(
            hook_text=hook_text,
            visual_prompt=visual_prompt,
            short_id=short_id,
            cta_index=cta_index,
            fal_key=fal_key,
        )
        result["thumbnail_path"] = str(thumb_path)
        result["thumbnail_status"] = "OK"
    except Exception as e:
        result["thumbnail_status"] = f"ERROR: {e}"
        return result

    # 2. Baked-in first frame (jeśli mamy plik wideo)
    if video_path and Path(video_path).exists():
        try:
            baked = bake_thumbnail_into_video(
                video_path=Path(video_path),
                thumbnail_path=thumb_path,
            )
            result["baked_video_path"] = str(baked)
            result["baked_status"] = "OK"
        except Exception as e:
            result["baked_status"] = f"ERROR: {e}"

    # 3. YouTube API thumbnails.set (try/catch — opcjonalne)
    if oauth_token:
        yt_res = upload_thumbnail_to_youtube(short_id, thumb_path, oauth_token)
        result["yt_thumbnail_status"] = yt_res

    return result


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Shorts Thumbnail Generator")
    parser.add_argument("--short-id", required=True, help="YouTube Video ID")
    parser.add_argument("--hook", required=True, help="Hook text (2-4 słowa)")
    parser.add_argument("--prompt", required=True, help="Visual prompt dla FLUX (EN)")
    parser.add_argument("--cta", type=int, default=None, help="CTA index 0-3")
    parser.add_argument("--video", help="Ścieżka do MP4 (baked-in frame)")
    parser.add_argument("--oauth-token", help="YouTube OAuth token")
    args = parser.parse_args()

    res = generate_short_thumbnail(
        short_id=args.short_id,
        hook_text=args.hook,
        visual_prompt=args.prompt,
        cta_index=args.cta,
        video_path=args.video,
        oauth_token=args.oauth_token,
    )
    print(json.dumps(res, indent=2, ensure_ascii=False, default=str))
