#!/usr/bin/env python3
"""
biblia_full_pipeline.py — Prawidłowy flow VSE dla kanału Prawy Biblijny

ARCHITEKTURA (poprawna — zaimplementowana 30.08.2026):
  Krok 1: MP3 → POST /v1/audio/generate → wyciągnij VTT
  Krok 2: VTT → YouTube captions.insert (napisy na kanale)
  Krok 3: poczekaj 30s → POST /v1/generate z URL YouTube
          (teraz YT ma napisy → VSE czyta je → thumbnail + VideoObject + embed)
  Krok 4: schema → POST /v1/inject → WP post zaplanowany

BŁĄD z sesji 29.08.2026 (NIE RÓB TAK):
  Używanie /v1/audio/generate end-to-end → brak thumbnail, brak VideoObject schema,
  video_url = 'audio://...' zamiast 'youtube://...'

Wymagania: pip install requests
Token VSE: generuj przez jose.jwt (patrz konstytucja workera)
Token YT: GET https://vse.impresjapr.pl/v1/youtube/channels → access_token
"""
import json, time, requests
from pathlib import Path
from typing import Optional

# ===== CONFIG =====
VSE_BASE = "https://vse.impresjapr.pl"
VSE_TOKEN = ""       # JWT — patrz konstytucja: jose.jwt.encode()
YT_ACCESS_TOKEN = "" # z GET /v1/youtube/channels
MP3_DIR = r"C:\Users\tomas2\Videos\Prawy\Biblia 30.08-04.09.2026"
PORTAL_ID = "prawy"
PLAYLIST_ID = "PLw7UeigJuyWkUzzvhS1vZX0H251raaYa7"

VIDEOS = [
    ("Biblia 30.08.2026 mt 16 21-27.mp3", "OJtb1k4qGMw", "2026-08-30T00:00:00+02:00", "Biblia 30.08.2026 Mt 16,21-27"),
    ("Biblia 31.08.2026 łk 4 13-30.mp3",  "jq6zeXByESM", "2026-08-31T00:00:00+02:00", "Biblia 31.08.2026 Łk 4,13-30"),
    ("Biblia 01.09.2026 łk 4 31-37.mp3",  "dL8-MeQobrU", "2026-09-01T00:00:00+02:00", "Biblia 01.09.2026 Łk 4,31-37"),
    ("Biblia 02.09.2026 łk 4 38-44.mp3",  "xJMONXgcIxc", "2026-09-02T00:00:00+02:00", "Biblia 02.09.2026 Łk 4,38-44"),
    ("Biblia 03.09.2026 łk 5 1-11.mp3",   "1k1VL4gonzE", "2026-09-03T00:00:00+02:00", "Biblia 03.09.2026 Łk 5,1-11"),
    ("Biblia 04.09.2026 łk 5 33-39.mp3",  "PSWJs3EYEeU", "2026-09-04T00:00:00+02:00", "Biblia 04.09.2026 Łk 5,33-39"),
    ("Biblia 05.09.2026 łk 6 1-5.mp3",    "nQeCFVntJOw", "2026-09-05T00:00:00+02:00", "Biblia 05.09.2026 Łk 6,1-5"),
]
# ==================

def vsh() -> dict:
    return {"Authorization": f"Bearer {VSE_TOKEN}"}

def step1_transcribe(mp3_path: Path) -> Optional[str]:
    """MP3 → Whisper → VTT. Zwraca tekst VTT lub None."""
    print(f"  [1] Transcribing: {mp3_path.name}")
    with open(mp3_path, "rb") as f:
        r = requests.post(f"{VSE_BASE}/v1/audio/generate", headers=vsh(),
            files={"file": (mp3_path.name, f, "audio/mpeg")},
            data={"lang": "pl", "llm_provider": "gemini"}, timeout=600)
    if r.status_code != 200:
        print(f"  [1] ERROR {r.status_code}: {r.text[:200]}")
        return None
    s = r.json().get("schema_data", {})
    vtt = s.get("vtt") or s.get("transcript") or s.get("vtt_content")
    print(f"  [1] VTT {'OK' if vtt else 'MISSING'} (keys: {list(s.keys())})")
    return vtt

def step2_upload_captions(video_id: str, vtt: str) -> bool:
    """VTT → YouTube captions.insert."""
    import io
    print(f"  [2] Uploading captions: {video_id}")
    meta = json.dumps({"snippet": {"videoId": video_id, "language": "pl", "name": "Polski", "isDraft": False}}).encode()
    r = requests.post(
        "https://www.googleapis.com/upload/youtube/v3/captions",
        params={"part": "snippet", "sync": "false"},
        headers={"Authorization": f"Bearer {YT_ACCESS_TOKEN}"},
        files=[("snippet", ("body.json", io.BytesIO(meta), "application/json")),
               ("media",   ("captions.vtt", io.BytesIO(vtt.encode()), "text/vtt"))],
        timeout=60)
    print(f"  [2] captions.insert: {r.status_code} {r.text[:100] if r.status_code != 200 else 'OK'}")
    return r.status_code in (200, 201)

def step3_generate_yt(video_id: str, title: str) -> Optional[dict]:
    """YouTube URL → /v1/generate → pełny pipeline (thumbnail, VideoObject, embed)."""
    print(f"  [3] VSE generate from YT: {video_id}")
    r = requests.post(f"{VSE_BASE}/v1/generate", headers=vsh(), json={
        "video_url": f"https://www.youtube.com/watch?v={video_id}",
        "publication_type": "film", "portal_id": PORTAL_ID,
        "post_title": title, "lang": "pl", "llm_provider": "gemini"}, timeout=300)
    if r.status_code != 200:
        print(f"  [3] ERROR {r.status_code}: {r.text[:200]}")
        return None
    d = r.json()
    print(f"  [3] OK status={d.get('status')}")
    return d.get("schema_data")

def step4_inject_wp(schema: dict, publish_at: str) -> Optional[int]:
    """schema → /v1/inject → WP post zaplanowany."""
    print(f"  [4] Inject to WP, publish={publish_at}")
    r = requests.post(f"{VSE_BASE}/v1/inject", headers=vsh(), json={
        "schema_data": schema, "portal_id": PORTAL_ID,
        "publish_date": publish_at, "status": "future"}, timeout=120)
    if r.status_code != 200:
        print(f"  [4] ERROR {r.status_code}: {r.text[:200]}")
        return None
    pid = r.json().get("post_id") or r.json().get("wp_post_id")
    print(f"  [4] WP post: {pid}")
    return pid

def yt_schedule(video_id: str, title: str, description: str, publish_at: str) -> bool:
    """Update YouTube: opis + scheduledPublishAt + playlista."""
    h = {"Authorization": f"Bearer {YT_ACCESS_TOKEN}", "Content-Type": "application/json"}
    r = requests.put("https://www.googleapis.com/youtube/v3/videos",
        params={"part": "snippet,status"}, headers=h,
        json={"id": video_id,
              "snippet": {"title": title, "description": description, "categoryId": "22"},
              "status": {"privacyStatus": "private", "publishAt": publish_at}}, timeout=60)
    print(f"  [YT] videos.update: {r.status_code}")
    if r.status_code == 200:
        requests.post("https://www.googleapis.com/youtube/v3/playlistItems",
            params={"part": "snippet"}, headers=h,
            json={"snippet": {"playlistId": PLAYLIST_ID,
                  "resourceId": {"kind": "youtube#video", "videoId": video_id}}}, timeout=30)
    return r.status_code == 200

if __name__ == "__main__":
    results = []
    for mp3_name, yt_id, pub_at, title in VIDEOS:
        mp3 = Path(MP3_DIR) / mp3_name
        print(f"\n{'='*55}\n{title}\n{'='*55}")
        if not mp3.exists():
            alt = list(Path(MP3_DIR).glob(f"*{pub_at[8:10]}.{pub_at[5:7]}*"))
            mp3 = alt[0] if alt else mp3
        vtt = step1_transcribe(mp3)
        if not vtt:
            results.append({"title": title, "status": "error", "error": "no_vtt"}); continue
        if YT_ACCESS_TOKEN:
            step2_upload_captions(yt_id, vtt)
            print("  Waiting 30s for YT caption indexing...")
            time.sleep(30)
        schema = step3_generate_yt(yt_id, title)
        if not schema:
            results.append({"title": title, "status": "error", "error": "no_schema"}); continue
        post_id = step4_inject_wp(schema, pub_at)
        if YT_ACCESS_TOKEN:
            yt_schedule(yt_id, title, schema.get("youtube_description", ""), pub_at)
        results.append({"title": title, "status": "ok", "yt_id": yt_id, "wp_post_id": post_id})
        time.sleep(5)
    print("\n=== SUMMARY ===")
    for r in results:
        print(f"  [{r['status']}] {r['title']} → WP {r.get('wp_post_id', r.get('error'))}")
    Path(MP3_DIR).joinpath("full_pipeline_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")