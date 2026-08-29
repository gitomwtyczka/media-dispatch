#!/usr/bin/env python3
"""
prawy_standard_pipeline.py — Pipeline B: Prawy TV (kanał z auto-napisami YT)

ARCHITEKTURA:
  Prawy TV ma auto-captions PL na YouTube → Whisper NIE jest potrzebny.

  Krok 1: POST /v1/generate z URL YouTube → pełne SEO (thumbnail, VideoObject, embed)
  Krok 2: POST /v1/inject → WP post zaplanowany
  Krok 3: videos.update → opis YouTube (z schema_data.youtube_description)

Różnica vs biblia_full_pipeline.py:
  - BRAK kroku Whisper/audio
  - BRAK kroku captions.insert
  - Szybszy (brak 30s oczekiwania na indeksację napisów)
  - Używaj gdy kanał ma auto-captions w języku PL
"""
import json, time, requests
from pathlib import Path
from typing import Optional

# ===== CONFIG =====
VSE_BASE = "https://vse.impresjapr.pl"
VSE_TOKEN = ""        # JWT — patrz konstytucja: jose.jwt.encode()
YT_ACCESS_TOKEN = ""  # z GET /v1/youtube/channels
PORTAL_ID = "prawy"

# Lista filmów do przetworzenia:
# (youtube_url, publish_at, post_title_override)
VIDEOS = [
    # Przykład:
    # ("https://www.youtube.com/watch?v=VIDEO_ID", "2026-09-06T12:00:00+02:00", None),
]
# ==================

def vsh() -> dict:
    return {"Authorization": f"Bearer {VSE_TOKEN}"}

def step1_generate(yt_url: str, title: Optional[str] = None) -> Optional[dict]:
    """YouTube URL → /v1/generate → pełne SEO z thumbnail i VideoObject."""
    print(f"  [1] VSE generate: {yt_url}")
    payload = {
        "video_url": yt_url,
        "publication_type": "film",
        "portal_id": PORTAL_ID,
        "lang": "pl",
        "llm_provider": "gemini",
    }
    if title:
        payload["post_title"] = title
    r = requests.post(f"{VSE_BASE}/v1/generate", headers=vsh(), json=payload, timeout=300)
    if r.status_code != 200:
        print(f"  [1] ERROR {r.status_code}: {r.text[:200]}")
        return None
    d = r.json()
    print(f"  [1] OK status={d.get('status')}")
    return d.get("schema_data")

def step2_inject(schema: dict, publish_at: str) -> Optional[int]:
    """schema → /v1/inject → WP post zaplanowany."""
    print(f"  [2] Inject to WP, publish={publish_at}")
    r = requests.post(f"{VSE_BASE}/v1/inject", headers=vsh(), json={
        "schema_data": schema, "portal_id": PORTAL_ID,
        "publish_date": publish_at, "status": "future"}, timeout=120)
    if r.status_code != 200:
        print(f"  [2] ERROR {r.status_code}: {r.text[:200]}")
        return None
    pid = r.json().get("post_id") or r.json().get("wp_post_id")
    print(f"  [2] WP post: {pid}")
    return pid

def step3_update_yt(video_id: str, title: str, description: str, publish_at: str) -> bool:
    """Update YouTube: tytuł SEO + opis + scheduledPublishAt."""
    print(f"  [3] YT update: {video_id}")
    h = {"Authorization": f"Bearer {YT_ACCESS_TOKEN}", "Content-Type": "application/json"}
    # ⚠️ ZAWSZE podaj description przy update snippet — inaczej YT wyczyści opis!
    r = requests.put(
        "https://www.googleapis.com/youtube/v3/videos",
        params={"part": "snippet,status"},
        headers=h,
        json={
            "id": video_id,
            "snippet": {"title": title, "description": description, "categoryId": "25"},
            "status": {"privacyStatus": "private", "publishAt": publish_at},
        },
        timeout=60
    )
    print(f"  [3] videos.update: {r.status_code}")
    return r.status_code == 200

if __name__ == "__main__":
    results = []
    for yt_url, pub_at, title in VIDEOS:
        video_id = yt_url.split("v=")[-1].split("&")[0]
        print(f"\n{'='*55}\n{video_id} → {pub_at}\n{'='*55}")
        schema = step1_generate(yt_url, title)
        if not schema:
            results.append({"url": yt_url, "status": "error", "error": "no_schema"})
            continue
        post_id = step2_inject(schema, pub_at)
        if YT_ACCESS_TOKEN:
            seo_title = schema.get("title") or title or video_id
            yt_desc = schema.get("youtube_description", "")
            step3_update_yt(video_id, seo_title, yt_desc, pub_at)
        results.append({"url": yt_url, "status": "ok", "wp_post_id": post_id})
        time.sleep(3)
    print("\n=== SUMMARY ===")
    for r in results:
        print(f"  [{r['status']}] {r['url']} → WP {r.get('wp_post_id', r.get('error'))}")
