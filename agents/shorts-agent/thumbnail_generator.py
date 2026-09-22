"""
thumbnail_generator.py - Generator miniatur YouTube Shorts Prawy.pl
Wersja: v11 | 22.09.2026

Layout z PSD v11 (wspolrzedne dokladne, bez korekcji safe-zone):
  Elementy statyczne laduja tam gdzie sa w PSD - tlo nie ma znaczenia.
  Badge:     left=92,  top=76,   right=498, bottom=288
  CTA:       left=131, top=211,  right=913, bottom=394
  Apla:      left=0,   top=611,  right=1080, bottom=1836  (granat #07152B)
  RedBar:    left=105, top=611,  right=116,  bottom=1836
  TitleZone: left=173, top=723,  right=992,  bottom=1504  (szer. 819px)
  GuestZone: left=179, top=1629, right=913,  bottom=1699

Tlo:
  Tryb A (domyslny): klatka z YouTube (video_id)
  Tryb B: bg_path= -> custom plik (wybrany kadr z mocnym spojrzeniem)
  Tryb C (nastepna iteracja): AI-generated background - przekaz bg_path

Typografia:
  Font: NimbusSansNarrow-Bold, BEZ czarnej obwodki (scisle wg PSD v11)
  Drop shadow zamiast stroke.
  Uniformny rozmiar: najdluzszy fragment wyznacza font_size dla wszystkich linii.
  Smart line grouping: 1-3 slowa = jedno/linia; 4+ slow = 2 slowa/linia.
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

# === POZYCJE Z PSD v11 (dokladne — bez korekcji) ===
BADGE      = (92,  76,  498, 288)      # left,top,right,bottom
CTA_DEST   = (131, 211, 913, 394)
APLA       = (0,   611, 1080, 1836)    # granat, pelne pokrycie wg PSD
REDBAR     = (105, 611, 116,  1836)
TITLE_ZONE = (173, 723, 992, 1504)     # szer. 819px wg PSD
GUEST_ZONE = (179, 1629, 913, 1699)

# Zrodlowe obszary w sprite-plikach PNG
CTA_SRC   = (40, 1086, 913, 1246)
BADGE_SRC = (40,   58, 426,  260)

STROKE   = 0    # brak czarnej obwodki — scisle wg PSD v11
LINE_GAP = 10   # px odstep miedzy liniami tytulu


# -------------------------------------------------
#  SLOT TLA — podmien get_background() w nast. iter.
# -------------------------------------------------

def get_background(video_id: str, bg_path: str | None = None) -> Image.Image:
    """
    Zwraca tlo jako Image 1080x1920 RGBA.

    Tryb A (domyslny, bg_path=None):
        Pobiera klatke z YouTube.
    Tryb B (bg_path podany):
        Laduje custom plik — wybrany kadr lub AI-generated bg.
        Nastepna iteracja: przekaz bg_path wskazujacy na wygenerowane tlo.
    """
    if bg_path:
        img = Image.open(bg_path).convert("RGBA")
        return _smart_fill(img)
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
                img = Image.open(io.BytesIO(r.content)).convert("RGBA")
                return _smart_fill(img)
        except:
            pass
    return Image.new("RGBA", (W, H), NAVY)


# -------------------------------------------------
#  COMPOSITING
# -------------------------------------------------

def _paste_element(base, src_path, src_bbox, dst_bbox):
    if not src_path.exists():
        return base
    src   = Image.open(src_path).convert("RGBA")
    el    = src.crop(src_bbox)
    dst_w = dst_bbox[2] - dst_bbox[0]
    dst_h = dst_bbox[3] - dst_bbox[1]
    el    = el.resize((dst_w, dst_h), Image.Resampling.LANCZOS)
    base  = base.convert("RGBA")
    base.paste(el, (dst_bbox[0], dst_bbox[1]), el)
    return base


def _apply_gradient(img):
    """Lewy gradient granatowy wzmocniony wg PSD v11."""
    panel = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pd    = ImageDraw.Draw(panel)
    for x in range(850):
        if x <= 380:   alpha = 200
        elif x <= 750: alpha = int(200 * (1 - (x - 380) / 370))
        else:           alpha = 0
        pd.line([(x, 0), (x, H)], fill=(7, 21, 43, alpha))
    return Image.alpha_composite(img.convert("RGBA"), panel)


def _apply_apla(img):
    """Apla granatowa (#07152B) pokrywajaca dolne ~66% — przykrywa napisy z wideo."""
    panel = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pd    = ImageDraw.Draw(panel)
    pd.rectangle([APLA[:2], APLA[2:]], fill=(7, 21, 43, 190))
    return Image.alpha_composite(img.convert("RGBA"), panel)


def _apply_redbar(img):
    draw = ImageDraw.Draw(img)
    draw.rectangle([REDBAR[:2], REDBAR[2:]], fill=RED_BAR)
    return img


# -------------------------------------------------
#  TYPOGRAFIA
# -------------------------------------------------

def _fit_size_for_line(text: str, max_w: int, min_s: int = 40, max_s: int = 550) -> int:
    """Binarnie szuka najwiekszego rozmiaru fontu gdzie text <= max_w px."""
    dummy = Image.new("RGB", (1, 1))
    dd    = ImageDraw.Draw(dummy)
    lo, hi, best = min_s, max_s, min_s
    while lo <= hi:
        mid = (lo + hi) // 2
        try:
            f = ImageFont.truetype(str(FONT_BOLD), mid)
        except:
            break
        bx = dd.textbbox((0, 0), text, font=f)
        if bx[2] - bx[0] <= max_w:
            best = mid
            lo   = mid + 1
        else:
            hi = mid - 1
    return best


def _smart_lines(hook_text: str) -> list[str]:
    """
    Dzielic hook na linie:
      1-3 slowa -> kazde slowo osobna linia
      4 slowa   -> 2 linie po 2
      5 slow    -> 2+2+1
      6+ slow   -> 3 rowne bloki
    """
    words = hook_text.upper().split()
    n = len(words)
    if n <= 3:
        return words
    if n == 4:
        return [f"{words[0]} {words[1]}", f"{words[2]} {words[3]}"]
    if n == 5:
        return [f"{words[0]} {words[1]}", f"{words[2]} {words[3]}", words[4]]
    chunk = (n + 2) // 3
    lines = []
    for i in range(0, n, chunk):
        lines.append(" ".join(words[i:i + chunk]))
    return lines[:3]


def render_title(img, hook_text: str) -> Image.Image:
    """
    Renderuje tytul hooka.
    Uniformny font size z najdluzszej linii — krotsze linie nie sa rozciagane.
    Wyrownanie lewe. Brak stroke, wzmocniony drop shadow.
    """
    lines = _smart_lines(hook_text)
    if not lines:
        return img

    tz_l, tz_t, tz_r, tz_b = TITLE_ZONE
    max_w = tz_r - tz_l
    max_h = tz_b - tz_t

    longest   = max(lines, key=lambda ln: len(ln))
    font_size = _fit_size_for_line(longest, max_w)
    font      = ImageFont.truetype(str(FONT_BOLD), font_size)

    dummy = Image.new("RGB", (1, 1))
    dd    = ImageDraw.Draw(dummy)

    line_heights = []
    for ln in lines:
        bb = dd.textbbox((0, 0), ln, font=font)
        line_heights.append(bb[3] - bb[1] + LINE_GAP)
    total_h = sum(line_heights)

    if total_h > max_h:
        ratio     = max_h / total_h
        font_size = max(30, int(font_size * ratio))
        font      = ImageFont.truetype(str(FONT_BOLD), font_size)
        line_heights = []
        for ln in lines:
            bb = dd.textbbox((0, 0), ln, font=font)
            line_heights.append(bb[3] - bb[1] + LINE_GAP)
        total_h = sum(line_heights)

    zone_mid = (tz_t + tz_b) // 2
    y = zone_mid - total_h // 2

    draw = ImageDraw.Draw(img)
    for ln, lh in zip(lines, line_heights):
        # Drop shadow (zastepuje stroke)
        for ox, oy in [(-4,4),(0,5),(4,4),(5,0),(4,-4),(0,-5),(-4,-4),(-5,0),
                       (-2,2),(0,3),(2,2),(3,0),(2,-2),(0,-3),(-2,-2),(-3,0)]:
            draw.text((tz_l + ox, y + oy), ln, font=font, fill=(0, 0, 0, 130))
        draw.text((tz_l, y), ln, font=font, fill="#FFFFFF")
        y += lh
    return img


def render_guests(img, text: str) -> Image.Image:
    if not text:
        return img
    gz_l, gz_t, gz_r, gz_b = GUEST_ZONE
    font_size = _fit_size_for_line(text, gz_r - gz_l, min_s=30, max_s=gz_b - gz_t)
    font      = ImageFont.truetype(str(FONT_BOLD), font_size)
    draw      = ImageDraw.Draw(img)
    for ox, oy in [(2,2),(0,2),(2,0)]:
        draw.text((gz_l + ox, gz_t + oy), text, font=font, fill=(0, 0, 0, 120))
    draw.text((gz_l, gz_t), text, font=font, fill=RED_TEXT)
    return img


# -------------------------------------------------
#  GLOWNA FUNKCJA
# -------------------------------------------------

def generate_thumbnail(
    video_id:   str,
    hook_text:  str,
    guest_text: str  = "",
    cta_idx:    int  = 0,
    output_dir: str | None = None,
    bg_path:    str | None = None,
) -> Path:
    """
    Generuje miniature JPG dla YouTube Short Prawy.pl.

    video_id    - ID wideo YouTube
    hook_text   - tekst hooka (dynamiczny)
    guest_text  - gosc/goscie (dynamiczny), '' = brak
    cta_idx     - 0=subskrybuj 1=lapka 2=prawy.pl 3=udostepnij
    output_dir  - katalog docelowy (None = C:\VSE\Shorts\thumbnails)
    bg_path     - custom tlo (None = klatka z YouTube)  *** SLOT ***
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
    img = render_guests(img, guest_text)

    out = out_dir / f"{video_id}_thumbnail.jpg"
    img.convert("RGB").save(out, "JPEG", quality=93)
    return out
