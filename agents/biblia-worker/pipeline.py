import json
import subprocess
import requests
import jwt as pyjwt
from datetime import datetime, timezone, timedelta
import config
import os
import sys
import io
import time
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

class BibliaPipeline:
    def __init__(self, dry_run=True):
        self.jwt_secret = None
        self.headers = None
        self.dry_run = dry_run
        self.yt_tokens = []
        self.channel_token = None
        self.yt_client = None

    def _run_ssh(self, cmd):
        if self.dry_run:
            print(f"[DRY RUN] SSH cmd: {cmd}")
            return '{"stdout": "dry run output"}'
        full_cmd = [
            "ssh", "-i", config.SSH_KEY,
            "-o", "StrictHostKeyChecking=no",
            config.VPS, cmd
        ]
        result = subprocess.run(full_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"SSH command failed: {cmd}\nError: {result.stderr}")
        return result.stdout.strip()

    def get_jwt_token(self):
        if self.dry_run:
            print("[DRY RUN] Fetching JWT_SECRET and generating token...")
            self.headers = {"Authorization": "Bearer mock", "Content-Type": "application/json"}
            return self.headers

        print("[*] Fetching JWT_SECRET via SSH...")
        output = self._run_ssh("grep JWT_SECRET /home/ubuntu/video-seo-engine/.env")
        if "JWT_SECRET=" in output:
            self.jwt_secret = output.split("JWT_SECRET=")[1].strip().strip('"\'')
        else:
            raise Exception("JWT_SECRET not found in .env")

        print("[*] Generating JWT token...")
        token = pyjwt.encode(
            {"sub": config.USER_ID, "email": "tobroz@gmail.com", "exp": datetime.now(timezone.utc) + timedelta(hours=24)},
            self.jwt_secret, algorithm="HS256"
        )
        self.headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        return self.headers

    def get_yt_tokens(self):
        if self.dry_run:
            print("[DRY RUN] get_yt_tokens")
            self.channel_token = "mock_token"
            self.yt_client = None
            return

        print("[*] YT tokens przez SSH + _build_credentials...")
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
            "ssh", "-i", config.SSH_KEY, "-o", "StrictHostKeyChecking=no", config.VPS,
            f"docker exec -w /app vse-api python3 -c {subprocess.list2cmdline([code])}"
        ]
        r = subprocess.run(cmd, capture_output=True, timeout=60)
        stdout = r.stdout.decode('utf-8', errors='replace').strip()
        
        self.yt_tokens = []
        for line in stdout.splitlines():
            if line.startswith("["):
                try:
                    self.yt_tokens = json.loads(line)
                    break
                except:
                    pass
        
        self.channel_token = None
        for t_info in self.yt_tokens:
            if t_info.get("channel_id") == config.YT_CHANNEL:
                self.channel_token = t_info.get("token")
                break
        
        if not self.channel_token:
            raise Exception(f"STOP: credentials dla kanału config.YT_CHANNEL ({config.YT_CHANNEL}) nie znaleziono!")
        
        creds = Credentials(self.channel_token)
        self.yt_client = build("youtube", "v3", credentials=creds)

    def _fail_fast(self, resp, msg):
        if not resp.ok:
            if resp.status_code >= 400:
                if 'invalid_grant' in resp.text:
                    raise Exception(f"STOP_BATCH: invalid_grant in {msg}")
                raise Exception(f"{msg} failed with 4xx: {resp.status_code} {resp.text}")
            raise Exception(f"{msg} failed: {resp.status_code} {resp.text}")

    def step_generate(self, yt_id, title, mp4_path=None):
        if self.dry_run:
            print(f"[DRY RUN] Step 2: Generating content for {yt_id}...")
            return {"transkrypcja": "Mock", "tytul": "Mock", "opis": "Mock"}
            
        print(f"[*] Step 2: Generating content for {yt_id}...")
        payload = {
            "video_url": f"https://www.youtube.com/watch?v={yt_id}",
            "portal_id": config.PORTAL_ID,
            "publication_type": config.PUB_TYPE,
            "lang": "pl",
            "llm_provider": config.LLM
        }
        resp = requests.post(f"{config.VSE_BASE}/v1/generate", json=payload, headers=self.headers)
        self._fail_fast(resp, "Generate")
        data = resp.json()
        
        # Transcript Guard
        if "brak transkryptu" in data.get("transkrypcja", "").lower():
            print(f"[!] Brak transkryptu na YT. Uruchamiam fallback z mp4_path={mp4_path}...")
            data = self.step1b_whisper_fallback(yt_id, mp4_path, title)
            if not data:
                raise Exception(f"FAILED: Brak transkryptu i fallback Whisper nieudany dla {yt_id}")
            
        return data

    def step1b_whisper_fallback(self, video_id: str, mp4_name: str, title: str):
        print(f"  [1b] FALLBACK Whisper dla: {mp4_name}")
        mp4_path = Path(mp4_name) if mp4_name else Path("dummy.mp4")
        if not mp4_path.exists():
            ame_log = Path(r"C:\Users\tomas2\Documents\Adobe\Adobe Media Encoder\26.0\AMEEncodingLog.txt")
            if ame_log.exists() and mp4_name:
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
                    print(f"  [1b] Blad czytania AME log: {e}")

        if not mp4_path.exists():
            print(f"  [1b] BLAD: Plik MP4 nie istnieje: {mp4_path}")
            return None

        mp3_path = mp4_path.with_suffix('.mp3')
        if not mp3_path.exists():
            print(f"  [1b] Konwertuje MP4 MP3 przez ffmpeg...")
            r = subprocess.run(
                ["ffmpeg", "-i", str(mp4_path), "-q:a", "2", "-map", "a", str(mp3_path), "-y"],
                capture_output=True, timeout=120
            )
            if r.returncode != 0:
                print(f"  [1b] ffmpeg ERROR: {r.stderr.decode('utf-8', errors='replace')[:200]}")
                return None

        print(f"  [1b] Whisper: {mp3_path.name} (timeout=600s)")
        with open(mp3_path, "rb") as f:
            r = requests.post(f"{config.VSE_BASE}/v1/audio/generate", headers=self.headers,
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
                cmd = ["ssh", "-i", config.SSH_KEY, "-o", "StrictHostKeyChecking=no", config.VPS,
                       f"docker exec vse-api cat /tmp/{media_id}.vtt"]
                r2 = subprocess.run(cmd, capture_output=True, timeout=30)
                vtt = r2.stdout.decode('utf-8', errors='replace') if r2.returncode == 0 else None

        if not vtt:
            print("  [1b] Brak VTT - fallback Whisper nieudany")
            return None

        print(f"  [1b] Upload VTT captions YT: {video_id}")
        try:
            media = MediaIoBaseUpload(io.BytesIO(vtt.encode("utf-8")), mimetype="text/vtt")
            self.yt_client.captions().insert(
                part="snippet",
                body={"snippet": {"videoId": video_id, "language": "pl", "name": "Polski", "isDraft": False}},
                media_body=media
            ).execute()
            print(f"  [1b] captions OK")
        except Exception as e:
            if "invalid_grant" in str(e).lower():
                raise Exception(f"STOP_BATCH: invalid_grant in captions upload: {e}")
            print(f"  [1b] captions ERROR: {e}")
            return None

        for retry_idx in range(1, 3):
            print(f"  [1b] Czekam 30s na YT caption indexing (proba {retry_idx}/2)...")
            time.sleep(30)
            payload = {
                "video_url": f"https://www.youtube.com/watch?v={video_id}",
                "portal_id": config.PORTAL_ID,
                "publication_type": config.PUB_TYPE,
                "lang": "pl",
                "llm_provider": config.LLM
            }
            resp = requests.post(f"{config.VSE_BASE}/v1/generate", json=payload, headers=self.headers)
            if resp.ok:
                d = resp.json()
                if "brak transkryptu" not in d.get("transkrypcja", "").lower():
                    return d

        print("  [1b] Whisper fallback retry wyczerpane")
        return None

    def check_existing_wp_post(self, video_id: str, title: str):
        if self.dry_run:
            print(f"[DRY RUN] Checking if WP post exists for {video_id}...")
            return None, None
            
        code = f"""
import asyncio, requests, json, uuid
from api.db import AsyncSessionLocal
from api.models.portal import WpPortal
from core.injector import _make_auth

async def check():
    async with AsyncSessionLocal() as db:
        portal = await db.get(WpPortal, uuid.UUID('{config.PORTAL_ID}'))
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
        
        # 2. Szukaj po tytule
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
            "ssh", "-i", config.SSH_KEY, "-o", "StrictHostKeyChecking=no", config.VPS,
            f"docker exec -w /app vse-api python3 -c {subprocess.list2cmdline([code])}"
        ]
        r = subprocess.run(cmd, capture_output=True, timeout=45)
        stdout = r.stdout.decode('utf-8', errors='replace').strip()
        for line in stdout.splitlines():
            if '{"found"' in line:
                data = json.loads(line)
                if data.get("found"):
                    return data["id"], data["status"]
        return None, None

    def step_inject(self, yt_id, title, schema_data, publish_date_iso, status):
        existing_id, existing_status = self.check_existing_wp_post(yt_id, title)
        if existing_id:
            print(f"[*] Post already exists for {yt_id} (#{existing_id}), skipping inject.")
            return existing_id
            
        if self.dry_run:
            print(f"[DRY RUN] Step 3: Injecting to WP for {yt_id}...")
            return "mock_wp_post_id"
            
        print(f"[*] Step 3: Injecting to WP for {yt_id}...")
        payload = {
            "video_url": f"https://www.youtube.com/watch?v={yt_id}",
            "schema_data": schema_data,
            "portal_id": config.PORTAL_ID,
            "publish_date": publish_date_iso,
            "status": status
        }
        resp = requests.post(f"{config.VSE_BASE}/v1/inject", json=payload, headers=self.headers)
        self._fail_fast(resp, "Inject")
        pid = resp.json().get("wp_post_id") or resp.json().get("post_id")
        return pid

    def step_wpcli(self, wp_post_id, yt_id, publish_date_local, publish_date_gmt, status):
        if self.dry_run:
            print(f"[DRY RUN] Step 4: WP-CLI Post-processing for post {wp_post_id}...")
            return
            
        print(f"[*] Step 4: WP-CLI Post-processing for post {wp_post_id}...")
        
        cmds = [
            f"docker exec {config.WP_CONTAINER} wp post update {wp_post_id} --post_status={status} --post_date='{publish_date_local}' --post_date_gmt='{publish_date_gmt}' --edit_date=true --allow-root",
            f"docker exec {config.WP_CONTAINER} wp post term add {wp_post_id} podcast_show prawy-biblijny --allow-root",
            f"docker exec {config.WP_CONTAINER} wp term create category Biblia --slug=biblia --allow-root || true",
            f"docker exec {config.WP_CONTAINER} wp post term add {wp_post_id} category biblia --allow-root",
            f"docker exec {config.WP_CONTAINER} wp post meta update {wp_post_id} podcast_youtube_url 'https://www.youtube.com/watch?v={yt_id}' --allow-root",
            f"docker exec {config.WP_CONTAINER} wp cache flush --allow-root"
        ]
        
        for cmd in cmds:
            self._run_ssh(cmd)

    def step_youtube(self, yt_id, schema_data, publish_date_iso, status):
        if self.dry_run:
            print(f"[DRY RUN] Step 5: Updating YouTube for {yt_id}...")
            return True
            
        print(f"[*] Step 5: Updating YouTube for {yt_id}...")
        try:
            v_resp = self.yt_client.videos().list(part="snippet,status", id=yt_id).execute()
            if not v_resp.get("items"):
                raise Exception("videoNotFound")
            
            snippet = v_resp["items"][0]["snippet"]
            
            # Update desc via VSE endpoint if needed or here
            yt_title = schema_data.get("seo_title") or schema_data.get("post_title")
            yt_desc = schema_data.get("youtube_description_body") or schema_data.get("youtube_description")
            
            if yt_title:
                snippet["title"] = yt_title
            if yt_desc:
                snippet["description"] = yt_desc
            snippet["defaultLanguage"] = "pl"
            snippet["defaultAudioLanguage"] = "pl"
            
            if status == "future" and publish_date_iso:
                status_dict = {"privacyStatus": "private", "publishAt": publish_date_iso, "embeddable": True}
            elif status == "publish":
                status_dict = {"privacyStatus": "public", "embeddable": True}
            else:
                status_dict = {"privacyStatus": "unlisted", "embeddable": True}
                
            self.yt_client.videos().update(
                part="snippet,status",
                body={
                    "id": yt_id,
                    "snippet": snippet,
                    "status": status_dict
                }
            ).execute()
            print(f"  [3] YT update OK")
            
            # Playlist update
            if getattr(config, 'PLAYLIST', None):
                items = self.yt_client.playlistItems().list(part="snippet", playlistId=config.PLAYLIST, maxResults=50).execute()
                found = False
                for item in items.get("items", []):
                    if item["snippet"]["resourceId"]["videoId"] == yt_id:
                        found = True
                        break
                if not found:
                    self.yt_client.playlistItems().insert(
                        part="snippet",
                        body={"snippet": {"playlistId": config.PLAYLIST, "resourceId": {"kind": "youtube#video", "videoId": yt_id}}}
                    ).execute()
                    print(f"  [4] Dodano do playlisty OK")
            
            return True
        except Exception as e:
            if "invalid_grant" in str(e).lower():
                raise Exception(f"STOP_BATCH: invalid_grant in YT update: {e}")
            raise e
            
    def step_verify(self, wp_post_id, yt_id, plan_status, plan_publish_at):
        if self.dry_run or not wp_post_id or str(wp_post_id) == "mock_wp_post_id":
            print(f"[DRY RUN] Step 6: Verifying {yt_id}...")
            return {"yt_verified": "mock", "wp_verified": "mock", "ok": True}
            
        print(f"[*] Step 6: Verification for WP {wp_post_id} and YT {yt_id}...")
        errors = []
        yt_stat_str = "unknown"
        
        # 1. YT verification
        try:
            r_v = self.yt_client.videos().list(part="snippet,status", id=yt_id).execute()
            if r_v.get("items"):
                v = r_v["items"][0]
                st = v["status"]
                sn = v["snippet"]
                priv = st.get('privacyStatus')
                pub_at = st.get('publishAt')
                yt_stat_str = priv
                if pub_at:
                    yt_stat_str += f"+{pub_at}"
                    
                # Plan check
                expected_priv = "private" if plan_status == "future" else ("public" if plan_status == "publish" else "unlisted")
                if priv != expected_priv:
                    errors.append(f"YT privacyStatus mismatch: {priv} != {expected_priv}")
                if plan_publish_at and pub_at != plan_publish_at:
                    errors.append(f"YT publishAt mismatch: {pub_at} != {plan_publish_at}")
                
                if not st.get('embeddable'):
                    errors.append("YT not embeddable")
                if sn.get('defaultLanguage') != 'pl':
                    errors.append(f"YT defaultLanguage {sn.get('defaultLanguage')} != pl")
                if sn.get('defaultAudioLanguage') != 'pl':
                    errors.append(f"YT defaultAudioLanguage {sn.get('defaultAudioLanguage')} != pl")
                    
            else:
                errors.append("YT video not found")
                
            # Playlist check
            if getattr(config, 'PLAYLIST', None):
                items = self.yt_client.playlistItems().list(part="snippet", playlistId=config.PLAYLIST, maxResults=50).execute()
                if not any(item["snippet"]["resourceId"]["videoId"] == yt_id for item in items.get("items", [])):
                    errors.append("YT not in PLAYLIST")
        except Exception as e:
            errors.append(f"YT check failed: {e}")

        # 2. WP verification
        wp_stat_str = "unknown"
        code = f"""
import asyncio, requests, json, uuid
from api.db import AsyncSessionLocal
from api.models.portal import WpPortal
from core.injector import _make_auth

async def get_p():
    async with AsyncSessionLocal() as db:
        portal = await db.get(WpPortal, uuid.UUID('{config.PORTAL_ID}'))
        auth = _make_auth(portal.wp_username, portal.wp_app_password)
        base_url = portal.url.rstrip('/')
        
        # Check exactly one by WP ID
        resp = requests.get(f"{{base_url}}/wp-json/wp/v2/posts/{wp_post_id}", auth=auth, timeout=15)
        if resp.status_code == 200:
            p = resp.json()
            out = {{'status': p.get('status'), 'date': p.get('date'), 'date_gmt': p.get('date_gmt'), 'meta': p.get('meta', {{}})}}
            
            # Check terms
            term_resp = requests.get(f"{{base_url}}/wp-json/wp/v2/podcast_show?post={wp_post_id}", auth=auth, timeout=15)
            if term_resp.status_code == 200:
                out['podcast_show'] = [t['slug'] for t in term_resp.json()]
                
            cat_resp = requests.get(f"{{base_url}}/wp-json/wp/v2/categories?post={wp_post_id}", auth=auth, timeout=15)
            if cat_resp.status_code == 200:
                out['categories'] = [t['slug'] for t in cat_resp.json()]
                
            print(json.dumps(out))
        else:
            print(json.dumps({{'error': 'err_' + str(resp.status_code)}}))
asyncio.run(get_p())
"""
        cmd = ["ssh", "-i", config.SSH_KEY, "-o", "StrictHostKeyChecking=no", config.VPS,
               f"docker exec -w /app vse-api python3 -c {subprocess.list2cmdline([code])}"]
        r_w = subprocess.run(cmd, capture_output=True, timeout=30)
        s_out = r_w.stdout.decode('utf-8', errors='replace').strip()
        for l in s_out.splitlines():
            if '{"status"' in l or '{"error"' in l:
                try:
                    d = json.loads(l)
                    if d.get("error"):
                        errors.append(f"WP fetch error: {d['error']}")
                        break
                        
                    wp_stat_str = f"{d.get('status')}"
                    if d.get('date'):
                        wp_stat_str += f" ({d.get('date')})"
                        
                    if d.get("status") != plan_status:
                        errors.append(f"WP status mismatch: {d.get('status')} != {plan_status}")
                    
                    if d.get("meta", {}).get("podcast_youtube_url") != f"https://www.youtube.com/watch?v={yt_id}":
                        errors.append("WP meta podcast_youtube_url mismatch")
                        
                    if "prawy-biblijny" not in d.get("podcast_show", []):
                        errors.append("WP missing podcast_show: prawy-biblijny")
                        
                    if "biblia" not in d.get("categories", []):
                        errors.append("WP missing category: biblia")
                        
                    break
                except:
                    pass
        
        ok = len(errors) == 0
        return {"yt_verified": yt_stat_str, "wp_verified": wp_stat_str, "ok": ok, "errors": errors}

    def run(self, yt_id, title, publish_date_local, publish_date_gmt, publish_date_iso, status='draft', mp4_path=None):
        try:
            if not self.headers:
                self.get_jwt_token()
            if not self.yt_client and not self.dry_run:
                self.get_yt_tokens()
                
            schema_data = self.step_generate(yt_id, title, mp4_path)
            wp_post_id = self.step_inject(yt_id, title, schema_data, publish_date_iso, status)
            self.step_wpcli(wp_post_id, yt_id, publish_date_local, publish_date_gmt, status)
            self.step_youtube(yt_id, schema_data, publish_date_iso, status)
            
            v_res = self.step_verify(wp_post_id, yt_id, status, publish_date_iso)
            print(f"[+] Successfully processed {yt_id}. Verification: YT={v_res.get('yt_verified')} WP={v_res.get('wp_verified')}")
            return v_res
        except Exception as e:
            print(f"[-] Pipeline failed for {yt_id}: {str(e)}")
            raise e
            
    def run_patch(self, yt_id, wp_post_id):
        if self.dry_run:
            print(f"[DRY RUN] WOULD DO: Patch YT {yt_id} and WP {wp_post_id}")
            return True
            
        print(f"[*] Patching YT {yt_id} and WP {wp_post_id}")
        if not self.yt_client:
            self.get_yt_tokens()
            
        cmds = [
            f"docker exec {config.WP_CONTAINER} wp post term add {wp_post_id} podcast_show prawy-biblijny --allow-root",
            f"docker exec {config.WP_CONTAINER} wp post meta update {wp_post_id} podcast_youtube_url 'https://www.youtube.com/watch?v={yt_id}' --allow-root",
            f"docker exec {config.WP_CONTAINER} wp term create category Biblia --slug=biblia --allow-root || true",
            f"docker exec {config.WP_CONTAINER} wp post term add {wp_post_id} category biblia --allow-root"
        ]
        if str(wp_post_id) == "127477":
            cmds.append(f"docker exec {config.WP_CONTAINER} wp post term remove {wp_post_id} category uncategorized --allow-root || true")
        for cmd in cmds:
            self._run_ssh(cmd)
            
        v_resp = self.yt_client.videos().list(part="snippet,status", id=yt_id).execute()
        if v_resp.get("items"):
            snippet = v_resp["items"][0]["snippet"]
            st = v_resp["items"][0]["status"]
            snippet["defaultLanguage"] = "pl"
            snippet["defaultAudioLanguage"] = "pl"
            st["embeddable"] = True
            
            self.yt_client.videos().update(
                part="snippet,status",
                body={"id": yt_id, "snippet": snippet, "status": st}
            ).execute()
            
        print(f"[+] Patched {yt_id} and {wp_post_id}")
        return True
