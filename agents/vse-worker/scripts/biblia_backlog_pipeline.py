#!/usr/bin/env python3
"""
biblia_backlog_pipeline.py — Pipeline A backlog 28.08 i 29.08.2026

Self-contained. Pobiera tokeny przez SSH na starcie, następnie Pipeline A.

Wersja: 2.0 (poprawiona po sesji 30.08.2026 — 4 pułapki wykryte przez workera)
Fixy:
- llm_provider: claude (nie gemini — brak GEMINI_API_KEY na VPS)
- publication_type: full_analysis (nie film)
- portal_id: UUID (nie string alias)
- YT access_token: przez SSH _build_credentials (nie /v1/youtube/channels)
"""
import json, time, subprocess, requests, io
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.credentials import Credentials

# ===== CONFIG =====
VSE_BASE    = "https://vse.impresjapr.pl"
SSH_KEY     = r"C:\Users\tomas2\.ssh\oracle-crimson.key"
VPS         = "ubuntu@147.224.162.100"
MP3_DIR     = r"C:\Users\tomas2\Videos\Prawy\Biblia 16-23 mp3"
PORTAL_ID   = "2b047d7d-15a1-4d2f-8463-f89c2275bb73"  # prawy.pl UUID
PLAYLIST_ID = "PLw7UeigJuyWkUzzvhS1vZX0H251raaYa7"

VIDEOS = [
    # (mp3_name, yt_id, publish_date_local, title, vtt_media_id)
    ("Biblia 28.08.2026.mp3", "S69T_H-DJy4", "2026-08-28T00:00:00+02:00", "Biblia 28.08.2026", "audio_df892c7b"),
    ("Biblia 29.08.2026.mp3", "HaY1VnzG_3o", "2026-08-29T00:00:00+02:00", "Biblia 29.08.2026", "audio_2c56ac0a"),
]
# kolumny: mp3_name, yt_id, pub_at_local, title, vtt_media_id (None = uruchom Whisper)

# ===== KROK 0: TOKENY =====

def get_jwt_token() -> str:
    print("[0] JWT token przez SSH...")
    cmd = [
        "ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no", VPS,
        "docker exec vse-api python3 -c \""
        "import os,datetime; from jose import jwt; "
        "s=os.environ.get('JWT_SECRET_KEY',''); "
        "p={'sub':'4b97ab0c-98ee-46c6-9be8-d86adc4cb38a',"
        "'exp':datetime.datetime.utcnow()+datetime.timedelta(hours=24)}; "
        "print(jwt.encode(p,s,algorithm='HS256'))"
        "\""
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    token = r.stdout.strip()
    if not token:
        raise RuntimeError(f"JWT failed: {r.stderr[:200]}")
    print(f"[0] JWT OK ({token[:30]}...)")
    return token

def get_yt_tokens() -> list:
    """Pobierz aktywne tokeny YT przez SSH + _build_credentials z DB."""
    print("[0b] YT tokens przez SSH + _build_credentials...")
    code = (
        "import asyncio\n"
        "from api.db import AsyncSessionLocal\n"
        "from api.models.youtube_channel import YouTubeChannel\n"
        "from api.core.youtube_publish import _build_credentials\n"
        "from google.auth.transport.requests import Request\n"
        "from sqlalchemy.future import select\n"
        "import json\n"
        "async def main():\n"
        "    async with AsyncSessionLocal() as db:\n"
        "        res = await db.execute(select(YouTubeChannel).where(YouTubeChannel.is_active == True))\n"
        "        out = []\n"
        "        for ch in res.scalars().all():\n"
        "            try:\n"
        "                creds = _build_credentials(ch)\n"
        "                creds.refresh(Request())\n"
        "                out.append({'id': str(ch.id), 'channel_id': ch.youtube_channel_id, 'title': ch.title, 'token': creds.token})\n"
        "            except Exception as e:\n"
        "                pass\n"
        "        print(json.dumps(out))\n"
        "asyncio.run(main())\n"
    )
    cmd = [
        "ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no", VPS,
        f"docker exec -w /app vse-api python3 -c {subprocess.list2cmdline([code])}"
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    lines = [l for l in r.stdout.strip().split('\n') if l.startswith('[')]
    if not lines:
        raise RuntimeError(f"YT tokens failed: {r.stderr[:200]}")
    tokens = json.loads(lines[-1])
    print(f"[0b] Pobrano {len(tokens)} tokenów YT: {[t['title'] for t in tokens]}")
    return tokens

# ===== KROKI PIPELINE =====

def vsh(t): return {"Authorization": f"Bearer {t}"}

def step1_load_or_transcribe(mp3_path: Path, vtt_media_id, vse_token: str):
    """Jeśli vtt_media_id znane — pobierz VTT z VPS. W przeciwnym razie uruchom Whisper."""
    if vtt_media_id:
        print(f"  [1] Wczytuję VTT z VPS (pomijam Whisper): {vtt_media_id}")
        cmd = ["ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no", VPS,
               f"docker exec vse-api cat /tmp/{vtt_media_id}.vtt"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if r.returncode == 0 and r.stdout.strip():
            print(f"  [1] VTT wczytany ({len(r.stdout)} znaków)")
            return r.stdout
        print(f"  [1] VTT na VPS niedostępny, uruchamiam Whisper...")

    print(f"  [1] Whisper: {mp3_path.name} (timeout=600s)")
    with open(mp3_path, "rb") as f:
        r = requests.post(f"{VSE_BASE}/v1/audio/generate", headers=vsh(vse_token),
            files={"file": (mp3_path.name, f, "audio/mpeg")},
            data={"lang": "pl", "llm_provider": "claude"}, timeout=600)
    if r.status_code != 200:
        print(f"  [1] ERROR {r.status_code}: {r.text[:300]}")
        return None
    res = r.json()
    s = res.get("schema_data", {})
    vtt = s.get("vtt") or s.get("transcript") or s.get("vtt_content")
    if not vtt:
        media_id = s.get("media_id") or res.get("video_id")
        if media_id:
            cmd = ["ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no", VPS,
                   f"docker exec vse-api cat /tmp/{media_id}.vtt"]
            r2 = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if r2.returncode == 0:
                vtt = r2.stdout
    print(f"  [1] VTT {'OK' if vtt else 'MISSING'} ({len(vtt) if vtt else 0} znaków)")
    return vtt

def step2_upload_captions(video_id: str, vtt: str, yt_tokens: list):
    print(f"  [2] Napisy VTT → YT: {video_id}")
    for t_info in yt_tokens:
        try:
            creds = Credentials(t_info["token"])
            youtube = build("youtube", "v3", credentials=creds)
            media = MediaIoBaseUpload(io.BytesIO(vtt.encode("utf-8")), mimetype="text/vtt")
            res = youtube.captions().insert(
                part="snippet",
                body={"snippet": {"videoId": video_id, "language": "pl", "name": "Polski", "isDraft": False}},
                media_body=media
            ).execute()
            print(f"  [2] captions.insert: OK ({t_info['title']}) caption_id={res.get('id')}")
            return True
        except Exception as e:
            print(f"  [2] {t_info['title']}: {e}")
    return False

def step3_generate_yt(video_id: str, title: str, vse_token: str):
    print(f"  [3] VSE generate z YT: {video_id}")
    r = requests.post(f"{VSE_BASE}/v1/generate", headers=vsh(vse_token), json={
        "video_url": f"https://www.youtube.com/watch?v={video_id}",
        "publication_type": "full_analysis",
        "portal_id": PORTAL_ID,
        "post_title": title, "lang": "pl", "llm_provider": "claude"}, timeout=300)
    if r.status_code != 200:
        print(f"  [3] ERROR {r.status_code}: {r.text[:300]}")
        return None
    d = r.json()
    print(f"  [3] OK | status={d.get('status')}")
    return d.get("schema_data")

def step4_inject_wp(schema: dict, pub_at: str, vse_token: str, video_id: str):
    print(f"  [4] WP inject + antydatowanie: {video_id}")
    r = requests.post(f"{VSE_BASE}/v1/inject", headers=vsh(vse_token), json={
        "video_url": f"https://www.youtube.com/watch?v={video_id}",
        "schema_data": schema,
        "portal_id": PORTAL_ID,
        "post_status": "publish"}, timeout=120)
    if r.status_code != 200:
        print(f"  [4] ERROR {r.status_code}: {r.text[:300]}")
        return None
    resp = r.json()
    pid = resp.get("wp_post_id") or resp.get("post_id")
    print(f"  [4] WP post_id: {pid} | {resp.get('post_url','')}")

    # Antydatowanie przez WP REST API wewnątrz kontenera
    if pid and pub_at:
        print(f"  [4b] Antydatuję WP #{pid} → {pub_at}")
        code = (
            "import asyncio, requests\n"
            "from api.db import AsyncSessionLocal\n"
            "from api.models.portal import WpPortal\n"
            "from core.injector import _make_auth\n"
            "import uuid\n"
            "async def update_date():\n"
            "    async with AsyncSessionLocal() as db:\n"
            f"        portal = await db.get(WpPortal, uuid.UUID('{PORTAL_ID}'))\n"
            "        auth = _make_auth(portal.wp_username, portal.wp_app_password)\n"
            f"        resp = requests.post(f'{{portal.url.rstrip(\"/ \")}}/wp-json/wp/v2/posts/{pid}',\n"
            f"            json={{'date': '{pub_at}'}}, auth=auth, timeout=20)\n"
            "        print(f'WP date: {{resp.status_code}} {{resp.text[:100]}}')\n"
            "asyncio.run(update_date())\n"
        )
        cmd = ["ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no", VPS,
               f"docker exec -w /app vse-api python3 -c {subprocess.list2cmdline([code])}"]
        r_date = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        print(f"  [4b] {r_date.stdout.strip() or r_date.stderr[:100]}")
    return pid

def step5_yt_publish(video_id: str, title: str, description: str, yt_tokens: list):
    print(f"  [5] YT public + SEO: {video_id}")
    for t_info in yt_tokens:
        try:
            creds = Credentials(t_info["token"])
            youtube = build("youtube", "v3", credentials=creds)
            v_resp = youtube.videos().list(part="snippet,status", id=video_id).execute()
            if not v_resp.get("items"):
                continue
            snippet = v_resp["items"][0]["snippet"]
            snippet["title"] = title
            snippet["description"] = description
            youtube.videos().update(
                part="snippet,status",
                body={"id": video_id, "snippet": snippet, "status": {"privacyStatus": "public"}}
            ).execute()
            print(f"  [5] OK ({t_info['title']})")
            return True
        except Exception as e:
            print(f"  [5] {t_info['title']}: {e}")
    return False

def step6_playlist(video_id: str, yt_tokens: list):
    print(f"  [6] Playlista: {video_id}")
    for t_info in yt_tokens:
        try:
            creds = Credentials(t_info["token"])
            youtube = build("youtube", "v3", credentials=creds)
            items = youtube.playlistItems().list(part="snippet", playlistId=PLAYLIST_ID, maxResults=50).execute()
            for item in items.get("items", []):
                if item["snippet"]["resourceId"]["videoId"] == video_id:
                    print(f"  [6] Już w playlistacie — pomijam")
                    return True
            youtube.playlistItems().insert(
                part="snippet",
                body={"snippet": {"playlistId": PLAYLIST_ID,
                      "resourceId": {"kind": "youtube#video", "videoId": video_id}}}
            ).execute()
            print(f"  [6] OK ({t_info['title']})")
            return True
        except Exception as e:
            print(f"  [6] {t_info['title']}: {e}")
    return False

# ===== MAIN =====

if __name__ == "__main__":
    vse_token = get_jwt_token()
    yt_tokens = get_yt_tokens()

    results = []
    for mp3_name, yt_id, pub_at, title, vtt_media_id in VIDEOS:
        mp3 = Path(MP3_DIR) / mp3_name
        print(f"\n{'='*60}\n{title}\n{'='*60}")

        vtt = step1_load_or_transcribe(mp3, vtt_media_id, vse_token)
        if not vtt:
            results.append({"title": title, "status": "error", "error": "no_vtt"})
            continue

        step2_upload_captions(yt_id, vtt, yt_tokens)
        print("  Czekam 30s na YT caption indexing...")
        time.sleep(30)

        schema = step3_generate_yt(yt_id, title, vse_token)
        if not schema:
            results.append({"title": title, "status": "error", "error": "no_schema"})
            continue

        post_id  = step4_inject_wp(schema, pub_at, vse_token, yt_id)
        yt_title = schema.get("post_title") or schema.get("title", title)
        yt_desc  = schema.get("youtube_description_body") or schema.get("youtube_description", "")
        step5_yt_publish(yt_id, yt_title, yt_desc, yt_tokens)
        step6_playlist(yt_id, yt_tokens)

        results.append({"title": title, "status": "ok", "yt_id": yt_id, "wp_post_id": post_id})
        time.sleep(5)

    print("\n=== SUMMARY ===")
    for res in results:
        print(f"  [{res['status']}] {res['title']} -> WP {res.get('wp_post_id', res.get('error'))}")

    out = Path(MP3_DIR) / "backlog_pipeline_results.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWyniki: {out}")
