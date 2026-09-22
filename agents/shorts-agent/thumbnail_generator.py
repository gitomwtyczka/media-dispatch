"""
thumbnail_generator.py — Generator miniatur YouTube Shorts Prawy.pl
Wersja: v11.1 | 22.09.2026

Zmiany v11.1 vs v11:
  - render_title: uniformny font_size = MIN z fit każdej linii osobno (px width, nie char count)
  - render_title: usunięty drop shadow (był widoczny jako obrys — apla granatowa zapewnia kontrast)
  - render_subtext: zamiast render_guests — elastyczny slot (gość, prowadzący, teaser)
  - render_guests: alias backward-compat

Layout z PSD v11 (wspolrzedne dokladne, bez korekcji safe-zone):
  Elementy statyczne laduja tam gdzie sa w PSD — tlo nie ma znaczenia.
  Badge:     left=92,  top=76,   right=498, bottom=288
  CTA:       left=131, top=211,  right=913, bottom=394
  Apla:      left=0,   top=611,  right=1080, bottom=1836  (granat #07152B)
  RedBar:    left=105, top=611,  right=116,  bottom=1836
  TitleZone: left=173, top=723,  right=992,  bottom=1504
  GuestZone: left=179, top=1629, right=913,  bottom=1699

Tlo:
  Tryb A (domyslny): klatka z YouTube (video_id)
  Tryb B: bg_path= -> custom plik
  Tryb C (nastepna iteracja): ffmpeg extract frame z lokalnego .mp4 (~50%)
    ffmpeg 8.0 dostepny na lokalnym PC
    Pliki .mp4 w C:\\VSE\\Shorts\\
    Slot bg_path= w generate_thumbnail() gotowy bez zmian w reszcie kodu

Typografia:
  Font: NimbusSansNarrow-Bold, BEZ stroke, BEZ shadow
  Uniformny rozmiar: min(fit_per_line) — krotsze slowo ta sama czcionka co dluzsze
  Smart split: 1-3 slowa = jedno/linia; 4+ = bloki 2
  Polskie znaki: Ł,Ż,Ą,Ń,Ś,Ó,Ś,Ż itd. — font i generator obsługują poprawnie
  Dolny czerwony slot: guest/prowadzący/teaser — elastyczny

OSTRZEŻENIE DLA NASTĘPNEGO AGENTA:
  Upload thumbnailów do YouTube Studio wymaga sesji Google — embedded Chrome (DevTools)
  jest blokowany przez OAuth Google. Używaj YouTube Data API v3 z OAuth token lub
  poprosić usera o ręczny upload przez YouTube Studio.
"""
import requests, io
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BRANDING_KIT = Path(r"D:\Biblioteki\prawy video\!_shortsy identyfikacja 9x16\prawy-shorts-kit")
FONT_BOLD        = BRANDING_KIT / "fonty" / "NimbusSansNarrow-Bold.otf"
OVERLAY_STATIC   = BRANDING_KIT / "01-overlay-staly.png"
CTA_FILES = [
    BRANDING_KIT / "02-cta-subskrybuj.png",
    BRANDING_KIT / "03-cta-lapka.png",
    BRANDING_KIT / "04-cta-prawypl.png",
    BRANDING_KIT / "05-cta-udostepnij.png",
]
OUTPUT = Path(r"C:\VSE\Shorts\thumbnails")

W, H     = 1080, 1920
NAVY     = (7, 21, 43, 255)
RED_BAR  = (226, 24, 55, 255)
RED_TEXT = "#E31335"

BADGE      = (92,  76,  498, 288)
CTA_DEST   = (131, 211, 913, 394)
APLA       = (0,   611, 1080, 1836)
REDBAR     = (105, 611, 116,  1836)
TITLE_ZONE = (173, 723, 992, 1504)
GUEST_ZONE = (179, 1629, 913, 1699)

CTA_SRC   = (40, 1086, 913, 1246)
BADGE_SRC = (40,   58, 426,  260)

STROKE   = 0
LINE_GAP = 10


def get_background(video_id: str, bg_path: str | None = None) -> Image.Image:
    """
    Tryb A (bg_path=None): klatka z YouTube.
    Tryb B (bg_path podany): custom plik.
    Tryb C (nast. iteracja): ffmpeg extract ~50% z lokalnego .mp4 -> bg_path.
    """
    if bg_path:
        return _smart_fill(Image.open(bg_path).convert("RGBA"))
    return _get_yt_thumb(video_id)


def _smart_fill(img: Image.Image) -> Image.Image:
    ow, oh = img.size
    scale  = max(W / ow, H / oh)
    nw, nh = int(ow * scale), int(oh * scale)
    img    = img.resize((nw, nh), Image.Resampling.LANCZOS)
    l, t   = (nw - W) // 2, (nh - H) // 2
    return img.crop((l, t, l + W, t + H))


def _get_yt_thumb(video_id: str) -> Image.Image:
    for q in ["oar2", "oardefault", "maxres2", "maxresdefault", "sddefault", "hqdefault"]:
        try:
            r = requests.get(f"https://i.ytimg.com/vi/{video_id}/{q}.jpg", timeout=10)
            if r.status_code == 200 and len(r.content) > 5000:
                return _smart_fill(Image.open(io.BytesIO(r.content)).convert("RGBA"))
        except:
            pass
    return Image.new("RGBA", (W, H), NAVY)


def _paste_element(base, src_path, src_bbox, dst_bbox):
    if not src_path.exists():
        return base
    src   = Image.open(src_path).convert("RGBA")
    el    = src.crop(src_bbox)
    el    = el.resize((dst_bbox[2]-dst_bbox[0], dst_bbox[3]-dst_bbox[1]), Image.Resampling.LANCZOS)
    base  = base.convert("RGBA")
    base.paste(el, (dst_bbox[0], dst_bbox[1]), el)
    return base


def _apply_gradient(img):
    panel = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pd    = ImageDraw.Draw(panel)
    for x in range(850):
        if x <= 380:   alpha = 200
        elif x <= 750: alpha = int(200 * (1 - (x - 380) / 370))
        else:           alpha = 0
        pd.line([(x, 0), (x, H)], fill=(7, 21, 43, alpha))
    return Image.alpha_composite(img.convert("RGBA"), panel)


def _apply_apla(img):
    panel = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(panel).rectangle([APLA[:2], APLA[2:]], fill=(7, 21, 43, 190))
    return Image.alpha_composite(img.convert("RGBA"), panel)


def _apply_redbar(img):
    ImageDraw.Draw(img).rectangle([REDBAR[:2], REDBAR[2:]], fill=RED_BAR)
    return img


def _fit_size_for_line(text: str, max_w: int, min_s: int = 40, max_s: int = 550) -> int:
    dummy = Image.new("RGB", (1, 1))
    dd    = ImageDraw.Draw(dummy)
    lo, hi, best = min_s, max_s, min_s
    while lo <= hi:
        mid = (lo + hi) // 2
        try:    f = ImageFont.truetype(str(FONT_BOLD), mid)
        except: break
        bx = dd.textbbox((0, 0), text, font=f)
        if bx[2] - bx[0] <= max_w:
            best = mid; lo = mid + 1
        else:
            hi = mid - 1
    return best


def _smart_lines(hook_text: str) -> list[str]:
    """
    1-3 slowa -> kazde na osobnej linii
    4        -> 2+2
    5        -> 2+2+1
    6+       -> 3 rowne bloki
    """
    words = hook_text.upper().split()
    n = len(words)
    if n <= 3:  return words
    if n == 4:  return [f"{words[0]} {words[1]}", f"{words[2]} {words[3]}"]
    if n == 5:  return [f"{words[0]} {words[1]}", f"{words[2]} {words[3]}", words[4]]
    chunk = (n + 2) // 3
    return [" ".join(words[i:i+chunk]) for i in range(0, n, chunk)][:3]


def render_title(img, hook_text: str) -> Image.Image:
    """
    Uniformny font_size = MIN z fit kazdej linii (px width).
    Krotsze slowo — ta sama wielkosc czcionki, wezsze.
    Bez stroke. Bez shadow. Apla granatowa zapewnia kontrast.
    """
    lines = _smart_lines(hook_text)
    if not lines:
        return img

    tz_l, tz_t, tz_r, tz_b = TITLE_ZONE
    max_w = tz_r - tz_l
    max_h = tz_b - tz_t

    dummy     = Image.new("RGB", (1, 1))
    dd        = ImageDraw.Draw(dummy)
    font_size = min(_fit_size_for_line(ln, max_w) for ln in lines)
    font      = ImageFont.truetype(str(FONT_BOLD), font_size)

    line_heights = [dd.textbbox((0,0), ln, font=font)[3] - dd.textbbox((0,0), ln, font=font)[1] + LINE_GAP
                    for ln in lines]
    total_h = sum(line_heights)

    if total_h > max_h:
        font_size = max(30, int(font_size * max_h / total_h))
        font      = ImageFont.truetype(str(FONT_BOLD), font_size)
        line_heights = [dd.textbbox((0,0), ln, font=font)[3] - dd.textbbox((0,0), ln, font=font)[1] + LINE_GAP
                        for ln in lines]
        total_h = sum(line_heights)

    y    = (tz_t + tz_b) // 2 - total_h // 2
    draw = ImageDraw.Draw(img)
    for ln, lh in zip(lines, line_heights):
        draw.text((tz_l, y), ln, font=font, fill="#FFFFFF")
        y += lh
    return img


def render_subtext(img, text: str) -> Image.Image:
    """
    Czerwony tekst dolny — elastyczny slot:
    gość ('PLŻŻAŃSKI — LISIECKI'), prowadzący ('PROF. KORNAT'),
    teaser ('SZOKUJĄCE!', 'NIE DO WIARY', 'MUSISZ TO ZOBACZYĆ').
    Bez stroke, bez shadow.
    """
    if not text:
        return img
    gz_l, gz_t, gz_r, gz_b = GUEST_ZONE
    font_size = _fit_size_for_line(text, gz_r - gz_l, min_s=30, max_s=gz_b - gz_t)
    font      = ImageFont.truetype(str(FONT_BOLD), font_size)
    ImageDraw.Draw(img).text((gz_l, gz_t), text, font=font, fill=RED_TEXT)
    return img


render_guests = render_subtext  # backward compat


def generate_thumbnail(
    video_id:   str,
    hook_text:  str,
    guest_text: str       = "",
    cta_idx:    int       = 0,
    output_dir: str|None  = None,
    bg_path:    str|None  = None,
) -> Path:
    """
    Generuje miniaturę JPG dla YouTube Short Prawy.pl.

    video_id    — ID wideo YouTube
    hook_text   — tekst hooka (dynamiczny, z polskimi znakami OK)
    guest_text  — gość/prowadzący/teaser ('' = brak czerwonego tekstu)
    cta_idx     — 0=subskrybuj 1=łapka 2=prawy.pl 3=udostępnij
    output_dir  — katalog docelowy (None = C:\\VSE\\Shorts\\thumbnails)
    bg_path     — custom tło (None = klatka z YouTube)  *** SLOT ***

    UPLOAD do YT:
      Embedded Chrome nie ma sesji Google — blokada OAuth.
      Opcja A: YouTube Data API v3 (thumbnails.set) z OAuth token.
      Opcja B: ręczny upload przez userą w YouTube Studio.
    """
    out_dir = Path(output_dir) if output_dir else OUTPUT
    out_dir.mkdir(parents=True, exist_ok=True)

    img = get_background(video_id, bg_path)
    img = _apply_gradient(img)
    img = _apply_apla(img)
    img = _apply_redbar(img)
    img = _paste_element(img, OVERLAY_STATIC, BADGE_SRC, BADGE)

    if cta_idx is not None and 0 <= cta_idx < len(CTA_FILES):
        img = _paste_element(img, CTA_FILES[cta_idx], CTA_SRC, CTA_DEST)

    img = render_title(img, hook_text)
    img = render_subtext(img, guest_text)

    out = out_dir / f"{video_id}_thumbnail.jpg"
    img.convert("RGB").save(out, "JPEG", quality=93)
    return out
