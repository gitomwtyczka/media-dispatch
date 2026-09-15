"""
thumbnail_generator.py — Generator thumbnails YouTube Shorts Prawy.pl
Wersja: v9 (finalny) | 15.09.2026

Layout (współrzędne z PSD wzorcowego):
  Badge:  left=92,  top=76,   right=498, bottom=288
  CTA:    left=131, top=211,  right=913, bottom=394
  Apla:   left=0,   top=664,  right=1080, bottom=1759
  RedBar: left=105, top=664,  right=116,  bottom=1759
  Title:  left=151, top=739,  right=1017, bottom=1508
  Guests: left=151, top=1629, right=942,  bottom=1699

Użycie:
  from thumbnail_generator import generate_thumbnail
  generate_thumbnail(video_id, hook_text, guest_text, cta_idx, output_path)
"""
import requests, io
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BRANDING_KIT = Path(r"D:\Biblioteki\prawy video\!_shortsy identyfikacja 9x16\prawy-shorts-kit")
FONT_BOLD = BRANDING_KIT / "fonty" / "NimbusSansNarrow-Bold.otf"
OVERLAY_STATIC = BRANDING_KIT / "01-overlay-staly.png"
CTA_FILES = [
    BRANDING_KIT / "02-cta-subskrybuj.png",
    BRANDING_KIT / "03-cta-lapka.png",
    BRANDING_KIT / "04-cta-prawypl.png",
    BRANDING_KIT / "05-cta-udostepnij.png",
]
OUTPUT = Path(r"C:\VSE\Shorts\thumbnails")

W, H = 1080, 1920
NAVY = (7, 21, 43, 255)
RED_BAR = (226, 24, 55, 255)
RED_TEXT = "#E31335"

# === POZYCJE Z PSD (nie zmieniaj!) ===
BADGE = (92, 76, 498, 288)    # left,top,right,bottom
CTA_DEST = (131, 211, 913, 394)
APLA = (0, 664, 1080, 1759)
REDBAR = (105, 664, 116, 1759)
TITLE_ZONE = (151, 739, 1017, 1508)  # left,top,right,bottom
GUEST_ZONE = (151, 1629, 942, 1699)

# CTA source w natywnym PNG
CTA_SRC = (40, 1086, 913, 1246)
# Badge source w natywnym PNG
BADGE_SRC = (40, 58, 426, 260)

STROKE = 5

def smart_fill(img):
    ow, oh = img.size
    scale = max(W/ow, H/oh)
    nw, nh = int(ow*scale), int(oh*scale)
    img = img.resize((nw, nh), Image.Resampling.LANCZOS)
    l, t = (nw-W)//2, (nh-H)//2
    return img.crop((l, t, l+W, t+H))

def get_yt_thumb(video_id):
    for q in ["oar2","oardefault","maxres2","maxresdefault","sddefault","hqdefault"]:
        try:
            r = requests.get(f"https://i.ytimg.com/vi/{video_id}/{q}.jpg", timeout=10)
            if r.status_code == 200 and len(r.content) > 5000:
                img = Image.open(io.BytesIO(r.content)).convert("RGBA")
                return smart_fill(img)
        except: pass
    return Image.new("RGBA", (W, H), NAVY)

def paste_element(base, src_path, src_bbox, dst_bbox):
    """
    Wytnij element z src_path w src_bbox i wklej w dst_bbox (przeskalowując).
    src_bbox i dst_bbox: (left, top, right, bottom)
    """
    if not src_path.exists():
        return base
    src = Image.open(src_path).convert('RGBA')
    el = src.crop(src_bbox)
    dst_w = dst_bbox[2] - dst_bbox[0]
    dst_h = dst_bbox[3] - dst_bbox[1]
    el = el.resize((dst_w, dst_h), Image.Resampling.LANCZOS)
    base = base.convert('RGBA')
    base.paste(el, (dst_bbox[0], dst_bbox[1]), el)
    return base

def apply_gradient(img):
    panel = Image.new('RGBA', (W,H), (0,0,0,0))
    pd = ImageDraw.Draw(panel)
    for x in range(799):  # z PSD: gradient width=799
        if x <= 350: alpha = 160
        elif x <= 700: alpha = int(160*(1-(x-350)/350))
        else: alpha = 0
        pd.line([(x,0),(x,H)], fill=(7,21,43,alpha))
    return Image.alpha_composite(img.convert('RGBA'), panel)

def apply_apla(img):
    panel = Image.new('RGBA', (W,H), (0,0,0,0))
    pd = ImageDraw.Draw(panel)
    pd.rectangle([APLA[:2], APLA[2:]], fill=(0,0,0,170))
    return Image.alpha_composite(img.convert('RGBA'), panel)

def apply_redbar(img):
    draw = ImageDraw.Draw(img)
    draw.rectangle([REDBAR[:2], REDBAR[2:]], fill=RED_BAR)
    return img

def fit_font_to_width(word, max_w, font_path, min_s=40, max_s=400):
    dummy = Image.new('RGB', (1,1))
    dd = ImageDraw.Draw(dummy)
    lo, hi, best = min_s, max_s, min_s
    while lo <= hi:
        mid = (lo+hi)//2
        try: f = ImageFont.truetype(str(font_path), mid)
        except: break
        bx = dd.textbbox((0,0), word, font=f)
        if bx[2]-bx[0] <= max_w: best=mid; lo=mid+1
        else: hi=mid-1
    return ImageFont.truetype(str(font_path), best), best

def render_title(img, hook_text):
    words = hook_text.upper().split()
    tz_l, tz_t, tz_r, tz_b = TITLE_ZONE
    max_w = tz_r - tz_l  # 866px
    max_h = tz_b - tz_t  # 769px

    fonts, heights = [], []
    for w in words:
        f, s = fit_font_to_width(w, max_w, FONT_BOLD)
        fonts.append(f)
        heights.append(s + 10)
    total_h = sum(heights)

    # Skaluj jeśli za wysoki
    if total_h > max_h:
        ratio = max_h / total_h
        fonts, heights = [], []
        for w in words:
            f, s = fit_font_to_width(w, int(max_w*ratio), FONT_BOLD)
            fonts.append(f)
            heights.append(s + 10)
        total_h = sum(heights)

    # Wycentruj pionowo w strefie
    zone_mid = (tz_t + tz_b) // 2
    y = zone_mid - total_h // 2

    draw = ImageDraw.Draw(img)
    for word, font, lh in zip(words, fonts, heights):
        draw.text((tz_l, y), word, font=font,
                  fill='#FFFFFF', stroke_width=STROKE, stroke_fill='#000000')
        y += lh
    return img

def render_guests(img, text):
    if not text: return img
    gz_l, gz_t, gz_r, gz_b = GUEST_ZONE
    max_w = gz_r - gz_l  # 791px
    max_h = gz_b - gz_t  # 70px
    font, _ = fit_font_to_width(text, max_w, FONT_BOLD, min_s=30, max_s=max_h)
    draw = ImageDraw.Draw(img)
    draw.text((gz_l, gz_t), text, font=font,
              fill=RED_TEXT, stroke_width=3, stroke_fill='#000000')
    return img

def generate_thumbnail(video_id, hook_text, guest_text='', cta_idx=0, output_dir=None):
    out_dir = Path(output_dir) if output_dir else OUTPUT
    out_dir.mkdir(parents=True, exist_ok=True)

    img = get_yt_thumb(video_id)
    img = apply_gradient(img)
    img = apply_apla(img)
    img = apply_redbar(img)
    
    # Badge
    img = paste_element(img, OVERLAY_STATIC, BADGE_SRC, BADGE)
    
    # CTA
    if cta_idx is not None and 0 <= cta_idx < len(CTA_FILES):
        img = paste_element(img, CTA_FILES[cta_idx], CTA_SRC, CTA_DEST)
        
    # Tekst
    img = render_title(img, hook_text)
    img = render_guests(img, guest_text)
    
    out = out_dir / f"{video_id}_thumbnail.jpg"
    img.convert('RGB').save(out, 'JPEG', quality=93)
    return out
