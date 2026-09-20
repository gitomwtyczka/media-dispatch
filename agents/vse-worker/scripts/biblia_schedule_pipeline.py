#!/usr/bin/env python3
"""
biblia_schedule_pipeline.py — Scheduling 13 filmów biblijnych Sep 21 – Oct 3 2026

Flow dla każdego video:
  1. Próba /v1/generate (YouTube auto-captions)
  2. Jeśli transcript_available=False → Whisper z MP4 (fallback awaryjny)
  3. /v1/inject → WP post_status=future z datą pub
  4. YouTube: scheduledPublish (privacyStatus=private + publishAt)
  5. Playlista Prawy Biblijny

Self-contained: pobiera JWT i YT tokens przez SSH na starcie.
Autor: biblia-worker | media-dispatch 20.09.2026
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
MP4_DIR     = r"C:\Users\tomas2\Videos\Prawy\Biblia 30.08-04.09.2026"
PORTAL_ID   = "2b047d7d-15a1-4d2f-8463-f89c2275bb73"  # prawy.pl UUID
PLAYLIST_ID = "PLw7UeigJuyWkUzzvhS1vZX0H251raaYa7"   # Prawy Biblijny

# ===== VIDEOS LIST =====
# (yt_id, mp4_filename, publish_date_iso, true_title_for_wp)
# publish_date: 00:00:00+02:00 = CEST midnight
VIDEOS = [
    # --- Sep 21-26: błędnie opisane na YT, właściwa treść wewnątrz ---
    ("IQ08oawsqZY",  "lk 6, 1-11_07.09.2026_poniedziałek.mp4",  "2026-09-21T00:00:00+02:00", "Łk 8,11-16 | Codzienne czytanie biblijne | 21.09.2026"),
    ("x_NXbSEgQrE",  "lk 6, 12-19_08.09.2026_wtorek.mp4",      "2026-09-22T00:00:00+02:00", "Łk 8,19-21 | Codzienne czytanie biblijne | 22.09.2026"),
    ("DmUKkMF8h8I",  "lk 6 20-26_09.09.2026_środa.mp4",        "2026-09-23T00:00:00+02:00", "Łk 9,1-6 | Codzienne czytanie biblijne | 23.09.2026"),
    ("O8h28o-hl0Y",  "lk 6, 27-38_10.09.2026_czwartek.mp4",   "2026-09-24T00:00:00+02:00", "Łk 9,7-9 | Codzienne czytanie biblijne | 24.09.2026"),
    ("zjwkbntfTfw",  "lk 6, 39-42_11.09.2026_piątek.mp4",      "2026-09-25T00:00:00+02:00", "Łk 9,18-22 | Codzienne czytanie biblijne | 25.09.2026"),
    ("Yy9QFIxq-V4",  "lk 6 , 43-49_12.09.2026_sobota.mp4",    "2026-09-26T00:00:00+02:00", "Łk 9,43b-45 | Codzienne czytanie biblijne | 26.09.2026"),
    # --- Sep 27 – Oct 3: właściwe opisy na YT ---
    ("BiHACQyOvJE",  "mt-21,28-32-27.09.2026-niedziela.mp4",   "2026-09-27T00:00:00+02:00", "Mt 21,28-32 | Codzienne czytanie biblijne | 27.09.2026"),
    ("-7QysZhJ7Wg",  "lk-9,46-50-28.09.2026-poniedziałek.mp4","2026-09-28T00:00:00+02:00", "Łk 9,46-50 | Codzienne czytanie biblijne | 28.09.2026"),
    ("xrnfUH3t95k",  "lk-9,51-56-29.09.2026-wtorek.mp4",      "2026-09-29T00:00:00+02:00", "Łk 9,51-56 | Codzienne czytanie biblijne | 29.09.2026"),
    ("dbTJHhqx7rY",  "lk-9,57-62-30.09.2026-środa.mp4",       "2026-09-30T00:00:00+02:00", "Łk 9,57-62 | Codzienne czytanie biblijne | 30.09.2026"),
    ("bvrLRDoOELs",  "lk-10,1-12-01.10.2026-czwartek.mp4",    "2026-10-01T00:00:00+02:00", "Łk 10,1-12 | Codzienne czytanie biblijne | 01.10.2026"),
    ("VA5D09x7r2c",  "lk-10,13-16-2.10.2026-piątek.mp4",      "2026-10-02T00:00:00+02:00", "Łk 10,13-16 | Codzienne czytanie biblijne | 02.10.2026"),
    ("N06YV7dzkMU",  "lk-10,17-24-03.10.2026-sobota.mp4",     "2026-10-03T00:00:00+02:00", "Łk 10,17-24 | Codzienne czytanie biblijne | 03.10.2026"),
]

# ===== TOKENY =====

def vsh(t): return {"Authorization": f"Bearer {t}"}

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
    r = subprocess.run(cmd, capture_output=True, timeout=30)
    token = r.stdout.decode('utf-8', errors='replace').strip()
    if not token:
        raise RuntimeError(f"JWT failed: {r.stderr.decode('utf-8', errors='replace')[:200]}")
    print(f"[0] JWT OK ({token[:30]}...)")
    return token

def get_yt_tokens() -> list:
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
    r = subprocess.run(cmd, capture_output=True, timeout=30)
    stdout = r.stdout.decode('utf-8', errors='replace').strip()
    lines = [l for l in stdout.split('\n') if l.startswith('[')]
    if not lines:
        raise RuntimeError(f"YT tokens failed: {r.stderr.decode('utf-8', errors='replace')[:200]}")
    tokens = json.loads(lines[-1])
    print(f"[0b] Pobrano {len(tokens)} tokenów YT: {[t['title'] for t in tokens]}")
    return tokens

# ===== KROKI PIPELINE =====

def step1_generate_yt(video_id: str, title: str, vse_token: str):
    """Próba pełnego pipeline przez YouTube captions. Zwraca (schema, transcript_ok)."""
    print(f"  [1] VSE generate z YT: {video_id}")
    r = requests.post(f"{VSE_BASE}/v1/generate", headers=vsh(vse_token), json={
        "video_url": f"https://www.youtube.com/watch?v={video_id}",
        "publication_type": "full_analysis",
        "portal_id": PORTAL_ID,
        "post_title": title, "lang": "pl", "llm_provider": "claude"}, timeout=300)
    if r.status_code != 200:
        print(f"  [1] ERROR {r.status_code}: {r.text[:300]}")
        return None, False
    d = r.json()
    schema = d.get("schema_data", {})
    transcript_ok = d.get("transcript_available", True) and schema.get("transcript_available", True)
    print(f"  [1] status={d.get('status')} | transcript_ok={transcript_ok}")
    return schema, transcript_ok

def step1b_whisper_fallback(video_id: str, mp4_path: Path, title: str, vse_token: str, yt_tokens: list):
    """Fallback awaryjny: MP4→MP3→Whisper→VTT→captions→generate."""
    print(f"  [1b] FALLBACK Whisper: {mp4_path.name}")
    # Konwertuj MP4 → MP3 przez ffmpeg
    mp3_path = mp4_path.with_suffix('.mp3')
    if not mp3_path.exists():
        print(f"  [1b] Konwertuję MP4→MP3...")
        r = subprocess.run(
            ["ffmpeg", "-i", str(mp4_path), "-q:a", "2", "-map", "a", str(mp3_path), "-y"],
            capture_output=True, timeout=120
        )
        if r.returncode != 0:
            print(f"  [1b] ffmpeg ERROR: {r.stderr.decode('utf-8', errors='replace')[:200]}")
            return None
    # Whisper przez VSE
    print(f"  [1b] Whisper: {mp3_path.name} (timeout=600s)")
    with open(mp3_path, "rb") as f:
        r = requests.post(f"{VSE_BASE}/v1/audio/generate", headers=vsh(vse_token),
            files={"file": (mp3_path.name, f, "audio/mpeg")},
            data={"lang": "pl", "llm_provider": "claude"}, timeout=600)
    if r.status_code != 200:
        print(f"  [1b] Whisper ERROR {r.status_code}: {r.text[:300]}")
        return None
    res = r.json()
    s = res.get("schema_data", {})
    vtt = s.get("vtt") or s.get("transcript") or s.get("vtt_content")
    if not vtt:
        media_id = s.get("media_id") or res.get("video_id")
        if media_id:
            cmd = ["ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no", VPS,
                   f"docker exec vse-api cat /tmp/{media_id}.vtt"]
            r2 = subprocess.run(cmd, capture_output=True, timeout=30)
            vtt = r2.stdout.decode('utf-8', errors='replace') if r2.returncode == 0 else None
    if not vtt:
        print("  [1b] Brak VTT — fallback nieudany")
        return None
    # Upload captions na YT
    print(f"  [1b] Upload VTT captions → YT: {video_id}")
    for t_info in yt_tokens:
        try:
            creds = Credentials(t_info["token"])
            youtube = build("youtube", "v3", credentials=creds)
            media = MediaIoBaseUpload(io.BytesIO(vtt.encode("utf-8")), mimetype="text/vtt")
            youtube.captions().insert(
                part="snippet",
                body={"snippet": {"videoId": video_id, "language": "pl", "name": "Polski", "isDraft": False}},
                media_body=media
            ).execute()
            print(f"  [1b] captions OK ({t_info['title']})")
            break
        except Exception as e:
            print(f"  [1b] captions ERROR ({t_info['title']}): {e}")
    print("  [1b] Czekam 30s na YT caption indexing...")
    time.sleep(30)
    # Ponów generate
    return step1_generate_yt(video_id, title, vse_token)[0]

def step2_inject_wp(schema: dict, pub_at: str, vse_token: str, video_id: str):
    """Inject do WP jako future post z datą schedulowania."""
    print(f"  [2] WP inject (future): {video_id} → {pub_at}")
    r = requests.post(f"{VSE_BASE}/v1/inject", headers=vsh(vse_token), json={
        "video_url": f"https://www.youtube.com/watch?v={video_id}",
        "schema_data": schema,
        "portal_id": PORTAL_ID,
        "post_status": "future"}, timeout=120)
    if r.status_code != 200:
        print(f"  [2] ERROR {r.status_code}: {r.text[:300]}")
        return None
    resp = r.json()
    pid = resp.get("wp_post_id") or resp.get("post_id")
    print(f"  [2] WP post_id: {pid}")
    # Ustaw datę schedulowania przez WP API wewnątrz kontenera
    if pid and pub_at:
        print(f"  [2b] Ustawiam datę WP #{pid} → {pub_at}")
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
            f"        resp = requests.post(f'{{portal.url.rstrip(\"/ !\")}}/wp-json/wp/v2/posts/{pid}',\n"
            f"            json={{'date': '{pub_at}', 'status': 'future'}}, auth=auth, timeout=20)\n"
            "        print(f'WP date: {resp.status_code} {resp.text[:100]}')\n"
            "asyncio.run(update_date())\n"
        )
        cmd = ["ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no", VPS,
               f"docker exec -w /app vse-api python3 -c {subprocess.list2cmdline([code])}"]
        r_date = subprocess.run(cmd, capture_output=True, timeout=30)
        print(f"  [2b] {r_date.stdout.decode('utf-8', errors='replace').strip() or r_date.stderr.decode('utf-8', errors='replace')[:100]}")
    return pid

def step3_yt_schedule(video_id: str, pub_at: str, yt_title: str, yt_desc: str, yt_tokens: list):
    """Ustaw YouTube scheduling: privacyStatus=private + publishAt."""
    print(f"  [3] YT schedule: {video_id} → {pub_at}")
    for t_info in yt_tokens:
        try:
            creds = Credentials(t_info["token"])
            youtube = build("youtube", "v3", credentials=creds)
            # Pobierz aktualny snippet żeby nie stracić metadanych
            v_resp = youtube.videos().list(part="snippet,status", id=video_id).execute()
            if not v_resp.get("items"):
                continue
            snippet = v_resp["items"][0]["snippet"]
            if yt_title:
                snippet["title"] = yt_title
            if yt_desc:
                snippet["description"] = yt_desc
            youtube.videos().update(
                part="snippet,status",
                body={
                    "id": video_id,
                    "snippet": snippet,
                    "status": {
                        "privacyStatus": "private",
                        "publishAt": pub_at  # RFC3339: 2026-09-21T00:00:00+02:00
                    }
                }
            ).execute()
            print(f"  [3] YT scheduled OK ({t_info['title']}) → {pub_at}")
            return True
        except Exception as e:
            print(f"  [3] ERROR ({t_info['title']}): {e}")
    return False

def step4_playlist(video_id: str, yt_tokens: list):
    print(f"  [4] Playlista Prawy Biblijny: {video_id}")
    for t_info in yt_tokens:
        try:
            creds = Credentials(t_info["token"])
            youtube = build("youtube", "v3", credentials=creds)
            # Sprawdź czy już w playliście
            items = youtube.playlistItems().list(part="snippet", playlistId=PLAYLIST_ID, maxResults=50).execute()
            for item in items.get("items", []):
                if item["snippet"]["resourceId"]["videoId"] == video_id:
                    print(f"  [4] Już w playliście — pomijam")
                    return True
            youtube.playlistItems().insert(
                part="snippet",
                body={"snippet": {"playlistId": PLAYLIST_ID,
                      "resourceId": {"kind": "youtube#video", "videoId": video_id}}}
            ).execute()
            print(f"  [4] Dodano do playlisty OK ({t_info['title']})")
            return True
        except Exception as e:
            print(f"  [4] ERROR ({t_info['title']}): {e}")
    return False

# ===== MAIN =====

if __name__ == "__main__":
    vse_token = get_jwt_token()
    yt_tokens = get_yt_tokens()

    results = []
    for yt_id, mp4_name, pub_at, title in VIDEOS:
        mp4 = Path(MP4_DIR) / mp4_name
        print(f"\n{'='*60}\n{title}\n  YT: {yt_id} | pub: {pub_at}\n{'='*60}")

        # Krok 1: próba przez YouTube auto-captions
        schema, transcript_ok = step1_generate_yt(yt_id, title, vse_token)

        if not transcript_ok:
            print(f"  ⚠️  Brak transkryptu YT — uruchamiam fallback Whisper")
            if mp4.exists():
                schema = step1b_whisper_fallback(yt_id, mp4, title, vse_token, yt_tokens)
            else:
                print(f"  ❌ MP4 nie istnieje: {mp4}")
                results.append({"title": title, "yt_id": yt_id, "status": "error", "error": "no_transcript_no_mp4"})
                continue

        if not schema:
            results.append({"title": title, "yt_id": yt_id, "status": "error", "error": "no_schema"})
            continue

        # Krok 2: WP future post
        wp_post_id = step2_inject_wp(schema, pub_at, vse_token, yt_id)

        # Krok 3: YT scheduled
        yt_title = schema.get("seo_title") or schema.get("post_title") or title
        yt_desc  = schema.get("youtube_description_body") or schema.get("youtube_description") or ""
        step3_yt_schedule(yt_id, pub_at, yt_title, yt_desc, yt_tokens)

        # Krok 4: Playlista
        step4_playlist(yt_id, yt_tokens)

        results.append({
            "title": title, "yt_id": yt_id, "pub_at": pub_at,
            "wp_post_id": wp_post_id, "status": "ok"
        })
        time.sleep(3)

    print("\n=== SUMMARY ===")
    for res in results:
        icon = "✅" if res["status"] == "ok" else "❌"
        print(f"  {icon} [{res['status']}] {res['title']} → WP#{res.get('wp_post_id', '?')} | {res.get('error', '')}")

    out = Path(MP4_DIR) / "schedule_pipeline_results.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWyniki: {out}")
