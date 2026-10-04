#!/usr/bin/env python3
"""
biblia_schedule_pipeline.py — Pipeline dla 7 filmów biblijnych Oct 04 – Oct 10 2026

Flow dla każdego video:
  0. Guard 3: sprawdź czy video istnieje na YT
  1. Guard 5: sprawdź czy post WP już istnieje (idempotencja)
  2. Próba /v1/generate (YouTube auto-captions)
     - Guard 2: fail-fast na błędach 4xx (np. 422)
     - Guard 1: jeśli 'brak transkryptu' -> Whisper fallback z MP4 (max 2 retry)
  3. WP inject:
     - dla 04.10: post_status=publish (publish now)
     - dla pozostałych: post_status=future + data schedulowania
  4. YouTube status:
     - dla 04.10: privacyStatus=public (bez publishAt)
     - dla pozostałych: privacyStatus=private + publishAt (RFC3339)
  5. Playlista Prawy Biblijny (PLw7UeigJuyWkUzzvhS1vZX0H251raaYa7)
  6. Weryfikacja końcowa i zapis do oct_pipeline_results.json

Guard 4: capture_output=True, decode('utf-8', errors='replace'), invalid_grant -> STOP.
"""
import json, time, subprocess, requests, io, sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.credentials import Credentials

# ===== CONFIG =====
VSE_BASE      = "https://vse.impresjapr.pl"
SSH_KEY       = r"C:\Users\tomas2\.ssh\oracle-crimson.key"
VPS           = "ubuntu@147.224.162.100"
MP4_DIR       = r"C:\Users\tomas2\Videos\Prawy\Biblia 04-10.10.2026"
PORTAL_ID     = "2b047d7d-15a1-4d2f-8463-f89c2275bb73"  # prawy.pl UUID
PLAYLIST_ID   = "PLw7UeigJuyWkUzzvhS1vZX0H251raaYa7"   # Prawy Biblijny
RESULTS_FILE  = r"C:\Users\tomas2\Videos\Prawy\oct_pipeline_results.json"

# ===== VIDEOS LIST =====
# (yt_id, mp4_filename, publish_date_iso, true_title_for_wp, publish_now)
VIDEOS = [
    ("h2ncQhExDw4", "2026-10-04_mt-21-33-43_kamien-wegielny_niedziela.mp4", "2026-10-04T00:00:00+02:00", "Mt 21,33-43 | Codzienne czytanie biblijne | 04.10.2026", True),
    ("JTapGa_m6uc", "2026-10-05_lk-10-25-37_milosierny-samarytanin_poniedzialek.mp4", "2026-10-05T00:00:00+02:00", "Łk 10,25-37 | Codzienne czytanie biblijne | 05.10.2026", False),
    ("UU3QEIA6CBU", "2026-10-06_lk-10-38-42_jednego-potrzeba_wtorek.mp4", "2026-10-06T00:00:00+02:00", "Łk 10,38-42 | Codzienne czytanie biblijne | 06.10.2026", False),
    ("h97hhEe_Dcw", "2026-10-07_lk-11-1-4_naucz-nas-modlic-sie_sroda.mp4", "2026-10-07T00:00:00+02:00", "Łk 11,1-4 | Codzienne czytanie biblijne | 07.10.2026", False),
    ("uirUFoX863w", "2026-10-08_lk-11-5-13_proscie-i-szukajcie_czwartek.mp4", "2026-10-08T00:00:00+02:00", "Łk 11,5-13 | Codzienne czytanie biblijne | 08.10.2026", False),
    ("CQTjzmnFbHA", "2026-10-09_lk-11-15-26_krolestwo-podzielone_piatek.mp4", "2026-10-09T00:00:00+02:00", "Łk 11,15-26 | Codzienne czytanie biblijne | 09.10.2026", False),
    ("ek0VxaoEIME", "2026-10-10_lk-11-27-28_prawdziwie-blogoslawieni_sobota.mp4", "2026-10-10T00:00:00+02:00", "Łk 11,27-28 | Codzienne czytanie biblijne | 10.10.2026", False),
]

def vsh(t): return {"Authorization": f"Bearer {t}"}

# ===== TOKENY =====

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
        err = r.stderr.decode('utf-8', errors='replace')[:200]
        raise RuntimeError(f"JWT failed: {err}")
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
        "                err_s = str(e)\n"
        "                out.append({'id': str(ch.id), 'title': ch.title, 'error': err_s, 'invalid_grant': 'invalid_grant' in err_s.lower()})\n"
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
        err = r.stderr.decode('utf-8', errors='replace')[:200]
        raise RuntimeError(f"YT tokens failed: {err}")
    all_tokens = json.loads(lines[-1])
    active_tokens = [t for t in all_tokens if t.get("token")]
    for t in all_tokens:
        if t.get("error"):
            print(f"  [0b] Kanał '{t.get('title')}' niedostępny: {t.get('error')[:80]}")
    if not active_tokens:
        raise RuntimeError("Brak aktywnych tokenów YT (wszystkie wygasły lub invalid_grant)!")
    print(f"[0b] Pobrano {len(active_tokens)} aktywnych tokenów YT: {[t['title'] for t in active_tokens]}")
    return active_tokens

# ===== GUARD 3: SPRAWDŹ CZY VIDEO ISTNIEJE NA YT =====

def check_video_exists_on_yt(video_id: str, yt_tokens: list):
    """Guard 3: przed przetwarzaniem sprawdź videos.list(id)."""
    for t_info in yt_tokens:
        try:
            creds = Credentials(t_info["token"])
            youtube = build("youtube", "v3", credentials=creds)
            res = youtube.videos().list(part="snippet,status", id=video_id).execute()
            items = res.get("items", [])
            if items:
                return True, items[0]
        except Exception as e:
            if "invalid_grant" in str(e).lower():
                raise RuntimeError(f"STOP: invalid_grant in YT API call: {e}")
            pass
    return False, None

# ===== GUARD 5: IDEMPOTENCJA WP =====

def check_existing_wp_post(video_id: str, title: str):
    """Guard 5: sprawdź czy post WP o danym tytule lub YT id już istnieje."""
    code = f"""
import asyncio, requests, json, uuid
from api.db import AsyncSessionLocal
from api.models.portal import WpPortal
from core.injector import _make_auth

async def check():
    async with AsyncSessionLocal() as db:
        portal = await db.get(WpPortal, uuid.UUID('{PORTAL_ID}'))
        auth = _make_auth(portal.wp_username, portal.wp_app_password)
        base_url = portal.url.rstrip('/')
        
        # 1. Szukaj po YT ID
        resp = requests.get(f"{{base_url}}/wp-json/wp/v2/posts?search={video_id}&status=publish,future,draft,pending,private", auth=auth, timeout=20)
        if resp.status_code == 200:
            posts = resp.json()
            for p in posts:
                content = p.get('content', {{}}).get('rendered', '')
                if '{video_id}' in content or '{video_id}' in p.get('link', ''):
                    print(json.dumps({{'found': True, 'id': p['id'], 'status': p['status'], 'date': p.get('date')}}))
                    return
        
        # 2. Szukaj po tytule (np. 'Łk 10,25-37' lub 'Mt 21,33-43')
        short_title = '{title}'.split('|')[0].strip()
        resp2 = requests.get(f"{{base_url}}/wp-json/wp/v2/posts?search={{short_title}}&status=publish,future,draft,pending,private", auth=auth, timeout=20)
        if resp2.status_code == 200:
            posts = resp2.json()
            for p in posts:
                p_title = p.get('title', {{}}).get('rendered', '')
                if short_title.lower() in p_title.lower():
                    print(json.dumps({{'found': True, 'id': p['id'], 'status': p['status'], 'date': p.get('date')}}))
                    return
                    
        print(json.dumps({{'found': False}}))

asyncio.run(check())
"""
    cmd = [
        "ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no", VPS,
        f"docker exec -w /app vse-api python3 -c {subprocess.list2cmdline([code])}"
    ]
    r = subprocess.run(cmd, capture_output=True, timeout=30)
    stdout = r.stdout.decode('utf-8', errors='replace').strip()
    for line in stdout.splitlines():
        if '{"found"' in line:
            data = json.loads(line)
            if data.get("found"):
                return data["id"], data["status"]
    return None, None

# ===== KROKI PIPELINE =====

def step1_generate_yt(video_id: str, title: str, vse_token: str):
    """
    Próba pełnego pipeline przez YouTube captions. Zwraca (schema, transcript_ok, error).
    Guard 2: fail-fast na 4xx.
    Guard 1: 'brak transkryptu' w tytule/opisie/leadzie -> transcript_ok = False.
    """
    print(f"  [1] VSE generate z YT: {video_id}")
    r = requests.post(f"{VSE_BASE}/v1/generate", headers=vsh(vse_token), json={
        "video_url": f"https://www.youtube.com/watch?v={video_id}",
        "publication_type": "full_analysis",
        "portal_id": PORTAL_ID,
        "post_title": title, "lang": "pl", "llm_provider": "claude"}, timeout=300)

    # Guard 2: 4xx fail-fast
    if 400 <= r.status_code < 500:
        err_msg = f"VSE 4xx FAIL-FAST ({r.status_code}): {r.text[:300]}"
        print(f"  [1] {err_msg}")
        return None, False, err_msg

    if r.status_code != 200:
        print(f"  [1] ERROR {r.status_code}: {r.text[:300]}")
        return None, False, f"HTTP {r.status_code}: {r.text[:200]}"

    d = r.json()
    schema = d.get("schema_data", {})
    transcript_ok = d.get("transcript_available", True) and schema.get("transcript_available", True)

    # Guard 1: sprawdzanie czy treść zawiera 'brak transkryptu'
    check_text = (
        str(schema.get("seo_title", "")) + " " +
        str(schema.get("post_title", "")) + " " +
        str(schema.get("youtube_description_body", "")) + " " +
        str(schema.get("youtube_description", "")) + " " +
        str(schema.get("lead", ""))
    ).lower()

    if "brak transkryptu" in check_text or "brak transkrypcji" in check_text or "transkrypcja niedostępna" in check_text:
        print("  [1] Wykryto frazę 'brak transkryptu' w odpowiedzi -> wymuszam fallback Whisper")
        transcript_ok = False

    print(f"  [1] status={d.get('status')} | transcript_ok={transcript_ok}")
    return schema, transcript_ok, None

def step1b_whisper_fallback(video_id: str, mp4_name: str, title: str, vse_token: str, yt_tokens: list):
    """
    Guard 1: Fallback awaryjny: MP4→MP3→Whisper→VTT→captions na YT→ponów generate (max 2 retry).
    """
    print(f"  [1b] FALLBACK Whisper dla: {mp4_name}")
    mp4_path = Path(MP4_DIR) / mp4_name
    if not mp4_path.exists():
        # Szukaj w AME logu
        ame_log = Path(r"C:\Users\tomas2\Documents\Adobe\Adobe Media Encoder\26.0\AMEEncodingLog.txt")
        if ame_log.exists():
            try:
                txt = ame_log.read_text(encoding="utf-16le", errors="replace")
                for line in txt.splitlines()[::-1]:
                    if mp4_name in line or Path(mp4_name).stem in line:
                        for token in line.split():
                            if token.lower().endswith(".mp4") and Path(token).exists():
                                mp4_path = Path(token)
                                print(f"  [1b] Zlokalizowano z AME log: {mp4_path}")
                                break
            except Exception as e:
                print(f"  [1b] Błąd czytania AME log: {e}")

    if not mp4_path.exists():
        print(f"  [1b] BŁĄD: Plik MP4 nie istnieje: {mp4_path}")
        return None

    mp3_path = mp4_path.with_suffix('.mp3')
    if not mp3_path.exists():
        print(f"  [1b] Konwertuję MP4→MP3 przez ffmpeg...")
        r = subprocess.run(
            ["ffmpeg", "-i", str(mp4_path), "-q:a", "2", "-map", "a", str(mp3_path), "-y"],
            capture_output=True, timeout=120
        )
        if r.returncode != 0:
            print(f"  [1b] ffmpeg ERROR: {r.stderr.decode('utf-8', errors='replace')[:200]}")
            return None

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
        print("  [1b] Brak VTT — fallback Whisper nieudany")
        return None

    # Upload captions na YT
    print(f"  [1b] Upload VTT captions → YT: {video_id}")
    uploaded = False
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
            uploaded = True
            break
        except Exception as e:
            if "invalid_grant" in str(e).lower():
                raise RuntimeError(f"STOP: invalid_grant in captions upload: {e}")
            print(f"  [1b] captions ERROR ({t_info['title']}): {e}")

    if not uploaded:
        print("  [1b] Nie udało się wgrać captions na YT")
        return None

    # Retry generate (max 2 próby)
    for retry_idx in range(1, 3):
        print(f"  [1b] Czekam 30s na YT caption indexing (próba {retry_idx}/2)...")
        time.sleep(30)
        sch, ok, err = step1_generate_yt(video_id, title, vse_token)
        if ok and sch:
            return sch

    print("  [1b] Whisper fallback retry wyczerpane")
    return None

def step2_inject_wp(schema: dict, pub_at: str, vse_token: str, video_id: str, publish_now: bool = False):
    """
    Inject do WP:
    - publish_now=True: post_status='publish'
    - publish_now=False: post_status='future' + data schedulowania
    """
    target_status = "publish" if publish_now else "future"
    print(f"  [2] WP inject ({target_status}): {video_id} → {pub_at if not publish_now else 'TERAZ'}")
    r = requests.post(f"{VSE_BASE}/v1/inject", headers=vsh(vse_token), json={
        "video_url": f"https://www.youtube.com/watch?v={video_id}",
        "schema_data": schema,
        "portal_id": PORTAL_ID,
        "post_status": target_status}, timeout=120)
    if r.status_code != 200:
        print(f"  [2] ERROR {r.status_code}: {r.text[:300]}")
        return None
    resp = r.json()
    pid = resp.get("wp_post_id") or resp.get("post_id")
    print(f"  [2] WP post_id: {pid}")

    # Aktualizacja daty i statusu na WP
    if pid:
        date_param = f", 'date': '{pub_at}'" if (pub_at and not publish_now) else ""
        print(f"  [2b] Ustawiam WP #{pid} status={target_status}{date_param}")
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
            f"        payload = {{'status': '{target_status}'{date_param}}}\n"
            f"        resp = requests.post(f'{{portal.url.rstrip(\"/ \")}}/wp-json/wp/v2/posts/{pid}',\n"
            "            json=payload, auth=auth, timeout=20)\n"
            "        print(f'WP date/status: {resp.status_code} {resp.text[:100]}')\n"
            "asyncio.run(update_date())\n"
        )
        cmd = ["ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no", VPS,
               f"docker exec -w /app vse-api python3 -c {subprocess.list2cmdline([code])}"]
        r_date = subprocess.run(cmd, capture_output=True, timeout=30)
        res_str = r_date.stdout.decode('utf-8', errors='replace').strip() or r_date.stderr.decode('utf-8', errors='replace')[:100]
        print(f"  [2b] {res_str}")
    return pid

def step3_yt_schedule(video_id: str, pub_at: str, yt_title: str, yt_desc: str, yt_tokens: list, publish_now: bool = False):
    """
    YouTube status:
    - publish_now=True: privacyStatus='public' (bez publishAt)
    - publish_now=False: privacyStatus='private' + publishAt
    """
    action_name = "PUBLIC" if publish_now else f"SCHEDULE {pub_at}"
    print(f"  [3] YT {action_name}: {video_id}")
    for t_info in yt_tokens:
        try:
            creds = Credentials(t_info["token"])
            youtube = build("youtube", "v3", credentials=creds)
            v_resp = youtube.videos().list(part="snippet,status", id=video_id).execute()
            if not v_resp.get("items"):
                continue
            snippet = v_resp["items"][0]["snippet"]
            if yt_title:
                snippet["title"] = yt_title
            if yt_desc:
                snippet["description"] = yt_desc
            
            if publish_now:
                status_dict = {"privacyStatus": "public"}
            else:
                status_dict = {"privacyStatus": "private", "publishAt": pub_at}

            youtube.videos().update(
                part="snippet,status",
                body={
                    "id": video_id,
                    "snippet": snippet,
                    "status": status_dict
                }
            ).execute()
            print(f"  [3] YT update OK ({t_info['title']}) → {action_name}")
            return True
        except Exception as e:
            if "invalid_grant" in str(e).lower():
                raise RuntimeError(f"STOP: invalid_grant in YT update: {e}")
            print(f"  [3] ERROR ({t_info['title']}): {e}")
    return False

def step4_playlist(video_id: str, yt_tokens: list):
    print(f"  [4] Playlista Prawy Biblijny: {video_id}")
    for t_info in yt_tokens:
        try:
            creds = Credentials(t_info["token"])
            youtube = build("youtube", "v3", credentials=creds)
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
            if "invalid_grant" in str(e).lower():
                raise RuntimeError(f"STOP: invalid_grant in playlist: {e}")
            print(f"  [4] ERROR ({t_info['title']}): {e}")
    return False

# ===== MAIN =====

if __name__ == "__main__":
    print("=== START PIPELINE BIBLIA ===")
    vse_token = get_jwt_token()
    yt_tokens = get_yt_tokens()

    results = []
    for yt_id, mp4_name, pub_at, title, publish_now in VIDEOS:
        date_str = pub_at[:10]
        reading_str = title.split('|')[0].strip()
        print(f"\n{'='*60}\n{title}\n  YT: {yt_id} | pub: {pub_at} | publish_now: {publish_now}\n{'='*60}")

        # Guard 3: sprawdź czy video istnieje na YT
        yt_found, yt_item = check_video_exists_on_yt(yt_id, yt_tokens)
        if not yt_found:
            print(f"  ❌ Guard 3: videoNotFound na wszystkich tokenach: {yt_id}")
            results.append({
                "date": date_str, "reading": reading_str, "yt_id": yt_id,
                "wp_post_id": None, "yt_status": "videoNotFound",
                "wp_status": "none", "ok": False, "error": "videoNotFound on all YT tokens"
            })
            continue

        # Guard 5: sprawdź idempotencję WP
        existing_wp_id, existing_wp_status = check_existing_wp_post(yt_id, title)
        if existing_wp_id:
            print(f"  ℹ️ Guard 5: Istniejący post WP znaleziony: #{existing_wp_id} (status: {existing_wp_status})")

        # Krok 1: VSE generate
        schema, transcript_ok, err = step1_generate_yt(yt_id, title, vse_token)

        # Guard 2: fail-fast jeśli 4xx
        if err and "FAIL-FAST" in err:
            results.append({
                "date": date_str, "reading": reading_str, "yt_id": yt_id,
                "wp_post_id": existing_wp_id, "yt_status": "fail",
                "wp_status": existing_wp_status or "fail", "ok": False, "error": err
            })
            continue

        # Guard 1: fallback Whisper jeśli brak transkrypcji
        if not transcript_ok:
            print(f"  ⚠️ Brak transkryptu YT — uruchamiam fallback Whisper...")
            schema = step1b_whisper_fallback(yt_id, mp4_name, title, vse_token, yt_tokens)

        if not schema:
            print(f"  ❌ Brak schemy — nie można kontynuować")
            results.append({
                "date": date_str, "reading": reading_str, "yt_id": yt_id,
                "wp_post_id": existing_wp_id, "yt_status": "fail",
                "wp_status": existing_wp_status or "fail", "ok": False, "error": "no_schema"
            })
            continue

        # Krok 2: WP inject
        wp_post_id = existing_wp_id
        if not wp_post_id:
            wp_post_id = step2_inject_wp(schema, pub_at, vse_token, yt_id, publish_now=publish_now)
        else:
            print(f"  [2] Pomijam /v1/inject (idempotencja) — post #{wp_post_id} już istnieje")

        # Krok 3: YT schedule / publish
        yt_title = schema.get("seo_title") or schema.get("post_title") or title
        yt_desc  = schema.get("youtube_description_body") or schema.get("youtube_description") or ""
        yt_ok = step3_yt_schedule(yt_id, pub_at, yt_title, yt_desc, yt_tokens, publish_now=publish_now)

        # Krok 4: Playlista
        pl_ok = step4_playlist(yt_id, yt_tokens)

        results.append({
            "date": date_str, "reading": reading_str, "yt_id": yt_id,
            "wp_post_id": wp_post_id,
            "yt_status": "public" if publish_now else f"private+{pub_at}",
            "wp_status": "publish" if publish_now else "future",
            "ok": bool(wp_post_id and yt_ok and pl_ok),
            "error": None if (wp_post_id and yt_ok and pl_ok) else "partial_failure"
        })
        time.sleep(3)

    print("\n=== PODSUMOWANIE I WERYFIKACJA KOŃCOWA ===")
    verified_results = []
    for res in results:
        v_id = res["yt_id"]
        # Weryfikacja YT
        yt_stat_str = "unknown"
        for t_info in yt_tokens:
            try:
                creds = Credentials(t_info["token"])
                youtube = build("youtube", "v3", credentials=creds)
                r_v = youtube.videos().list(part="status", id=v_id).execute()
                if r_v.get("items"):
                    st = r_v["items"][0]["status"]
                    yt_stat_str = f"{st.get('privacyStatus')}"
                    if st.get('publishAt'):
                        yt_stat_str += f"+{st.get('publishAt')}"
                    break
            except Exception:
                pass

        # Weryfikacja WP
        wp_stat_str = res["wp_status"]
        if res.get("wp_post_id"):
            code = f"""
import asyncio, requests, json, uuid
from api.db import AsyncSessionLocal
from api.models.portal import WpPortal
from core.injector import _make_auth

async def get_p():
    async with AsyncSessionLocal() as db:
        portal = await db.get(WpPortal, uuid.UUID('{PORTAL_ID}'))
        auth = _make_auth(portal.wp_username, portal.wp_app_password)
        resp = requests.get(f"{{portal.url.rstrip('/')}}/wp-json/wp/v2/posts/{res['wp_post_id']}", auth=auth, timeout=15)
        if resp.status_code == 200:
            p = resp.json()
            print(json.dumps({{'status': p.get('status'), 'date': p.get('date')}}))
        else:
            print(json.dumps({{'status': f'err_{{resp.status_code}}'}}))
asyncio.run(get_p())
"""
            cmd = ["ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no", VPS,
                   f"docker exec -w /app vse-api python3 -c {subprocess.list2cmdline([code])}"]
            r_w = subprocess.run(cmd, capture_output=True, timeout=25)
            s_out = r_w.stdout.decode('utf-8', errors='replace').strip()
            for l in s_out.splitlines():
                if '{"status"' in l:
                    d = json.loads(l)
                    wp_stat_str = f"{d.get('status')}"
                    if d.get('date'):
                        wp_stat_str += f" ({d.get('date')})"
                    break

        v_entry = {
            "date": res["date"],
            "reading": res["reading"],
            "yt_id": res["yt_id"],
            "wp_post_id": res["wp_post_id"],
            "yt_verified": yt_stat_str,
            "wp_verified": wp_stat_str,
            "ok": res["ok"]
        }
        verified_results.append(v_entry)
        print(f"  {'✅' if res['ok'] else '❌'} {res['date']} | {res['reading']} | YT: {yt_stat_str} | WP: #{res['wp_post_id']} ({wp_stat_str})")

    # Zapis do JSON
    Path(RESULTS_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(verified_results, f, ensure_ascii=False, indent=2)
    print(f"\nWyniki zapisane do: {RESULTS_FILE}")
