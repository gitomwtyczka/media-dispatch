import json
import subprocess
import requests
import jwt as pyjwt
from datetime import datetime, timezone, timedelta
from . import config

class BibliaPipeline:
    def __init__(self):
        self.jwt_secret = None
        self.headers = None

    def _run_ssh(self, cmd):
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

    def step_generate(self, yt_id):
        print(f"[*] Step 2: Generating content for {yt_id}...")
        payload = {
            "video_url": f"https://www.youtube.com/watch?v={yt_id}",
            "portal_id": config.PORTAL_ID,
            "publication_type": config.PUB_TYPE,
            "lang": "pl",
            "llm_provider": config.LLM
        }
        resp = requests.post(f"{config.VSE_BASE}/v1/generate", json=payload, headers=self.headers)
        if not resp.ok:
            raise Exception(f"Generate failed: {resp.text}")
        return resp.json()

    def step_inject(self, yt_id, schema_data, publish_date_iso, status):
        print(f"[*] Step 3: Injecting to WP for {yt_id}...")
        payload = {
            "video_url": f"https://www.youtube.com/watch?v={yt_id}",
            "schema_data": schema_data,
            "portal_id": config.PORTAL_ID,
            "publish_date": publish_date_iso,
            "status": status
        }
        resp = requests.post(f"{config.VSE_BASE}/v1/inject", json=payload, headers=self.headers)
        if not resp.ok:
            raise Exception(f"Inject failed: {resp.text}")
        return resp.json().get("wp_post_id")

    def step_wpcli(self, wp_post_id, yt_id, publish_date_local, publish_date_gmt, status):
        print(f"[*] Step 4: WP-CLI Post-processing for post {wp_post_id}...")
        
        cmds = [
            f"docker exec {config.WP_CONTAINER} wp post update {wp_post_id} --post_status={status} --post_date='{publish_date_local}' --post_date_gmt='{publish_date_gmt}' --edit_date=true --allow-root",
            f"docker exec {config.WP_CONTAINER} wp post term add {wp_post_id} podcast_show prawy-biblijny --allow-root",
            f"docker exec {config.WP_CONTAINER} wp post meta update {wp_post_id} podcast_youtube_url 'https://www.youtube.com/watch?v={yt_id}' --allow-root",
            f"docker exec {config.WP_CONTAINER} wp cache flush --allow-root"
        ]
        
        for cmd in cmds:
            self._run_ssh(cmd)

    def step_youtube(self, yt_id, schema_data):
        print(f"[*] Step 5: Updating YouTube for {yt_id}...")
        payload = {
            "video_id": yt_id,
            "schema_data": schema_data,
            "channel_ids": [config.YT_CHANNEL]
        }
        resp = requests.post(f"{config.VSE_BASE}/v1/youtube/publish-description", json=payload, headers=self.headers)
        if not resp.ok:
            raise Exception(f"YouTube update failed: {resp.text}")
        return resp.json()

    def run(self, yt_id, publish_date_local, publish_date_gmt, publish_date_iso, status='future'):
        try:
            if not self.headers:
                self.get_jwt_token()
            schema_data = self.step_generate(yt_id)
            wp_post_id = self.step_inject(yt_id, schema_data, publish_date_iso, status)
            self.step_wpcli(wp_post_id, yt_id, publish_date_local, publish_date_gmt, status)
            self.step_youtube(yt_id, schema_data)
            print(f"[+] Successfully processed {yt_id}")
        except Exception as e:
            print(f"[-] Pipeline failed for {yt_id}: {str(e)}")
            raise
