#!/usr/bin/env python3
import gspread
import json, time, subprocess, requests, io, os, sys, re
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.credentials import Credentials
from datetime import datetime, timezone

# ===== CONFIG =====
VSE_BASE    = "https://vse.impresjapr.pl"
SSH_KEY     = r"C:\Users\tomas2\.ssh\oracle-crimson.key"
VPS         = "ubuntu@147.224.162.100"
PORTAL_ID   = "2b047d7d-15a1-4d2f-8463-f89c2275bb73" # UUID for Prawy.pl
SHEET_ID    = "1zqwvS784EaZh1EJIcXk1DliAau1r4X15ENFJjloDSaM"
GID         = "809929940" # Zakładka Emisja
SERVICE_ACC = os.environ.get('GOOGLE_SA_FILE', '/home/ubuntu/media-dispatch/config/service_account.json')

# ===== TOKENS =====
def get_jwt_token() -> str:
    token = os.environ.get('PRESSAI_JWT_USER')
    if not token:
        raise RuntimeError("Brak tokenu PRESSAI_JWT_USER w .env")
    return token

def vsh(t): return {"Authorization": f"Bearer {t}"}

# ===== PIPELINE =====
def step_generate_yt(video_id: str, title: str, vse_token: str):
    print(f"  [GEN] VSE generate z YT: {video_id}")
    r = requests.post(f"{VSE_BASE}/v1/generate", headers=vsh(vse_token), json={
        "video_url": f"https://www.youtube.com/watch?v={video_id}",
        "publication_type": "full_analysis",
        "portal_id": PORTAL_ID,
        "post_title": title, "lang": "pl", "llm_provider": "claude"}, timeout=300)
    if r.status_code != 200:
        print(f"  [GEN] ERROR {r.status_code}: {r.text[:300]}")
        return None
    return r.json().get("schema_data")

def step_inject_wp(schema: dict, pub_at: str, vse_token: str, video_id: str):
    print(f"  [INJ] WP inject + antydatowanie: {video_id}")
    r = requests.post(f"{VSE_BASE}/v1/inject", headers=vsh(vse_token), json={
        "video_url": f"https://www.youtube.com/watch?v={video_id}",
        "schema_data": schema,
        "portal_id": PORTAL_ID,
        "post_status": "draft"}, timeout=120)
    if r.status_code != 200:
        print(f"  [INJ] ERROR {r.status_code}: {r.text[:300]}")
        return None
    resp = r.json()
    pid = resp.get("wp_post_id") or resp.get("post_id")
    print(f"  [INJ] WP post_id: {pid} | {resp.get('post_url','')}")

    # Antydatowanie
    if pid and pub_at:
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
        r_date = subprocess.run(cmd, capture_output=True, text=True, timeout=30, encoding="utf-8")
        print(f"  [INJ] {r_date.stdout.strip() or r_date.stderr[:100]}")
    return pid

def step_upload_image(post_id: str, image_path: str):
    path = Path(image_path.strip('\"\' '))
    if not path.exists():
        print(f"  [IMG] ERROR: Plik obrazka nie istnieje: {path}")
        return False
        
    print(f"  [IMG] Upload obrazka: {path.name}")
    remote_tmp = f"/tmp/upload_{int(time.time())}_{path.name}"
    cmd_scp = ["scp", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no", str(path), f"{VPS}:{remote_tmp}"]
    subprocess.run(cmd_scp, check=True)
    
    code = (
        "import asyncio, requests\n"
        "from api.db import AsyncSessionLocal\n"
        "from api.models.portal import WpPortal\n"
        "from core.injector import _make_auth\n"
        "import uuid, os\n"
        "async def main():\n"
        "    async with AsyncSessionLocal() as db:\n"
        f"        portal = await db.get(WpPortal, uuid.UUID('{PORTAL_ID}'))\n"
        "        auth = _make_auth(portal.wp_username, portal.wp_app_password)\n"
        "        wp_url = portal.url.rstrip('/')\n"
        f"        filepath = '{remote_tmp}'\n"
        "        filename = os.path.basename(filepath)\n"
        "        with open(filepath, 'rb') as f: data = f.read()\n"
        "        headers = {'Content-Disposition': f'attachment; filename=\"{{filename}}\"', 'Content-Type': 'image/jpeg'}\n"
        f"        res = requests.post(f'{{wp_url}}/wp-json/wp/v2/media?post={post_id}', auth=auth, headers=headers, data=data)\n"
        "        if res.status_code in (200, 201):\n"
        "            print(f'MEDIA_OK: {{res.json().get(\"id\")}}')\n"
        "        else:\n"
        "            print(f'FAIL_MEDIA: {{res.status_code}} {{res.text[:100]}}')\n"
        "asyncio.run(main())\n"
    )
    cmd_ssh = ["ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no", VPS,
               f"docker exec -w /app vse-api python3 -c {subprocess.list2cmdline([code])}"]
    r = subprocess.run(cmd_ssh, capture_output=True, text=True, encoding="utf-8")
    print(f"  [IMG] {r.stdout.strip()}")
    return True

# ===== MAIN =====
def get_sheet_data():
    gc = gspread.service_account(filename=SERVICE_ACC)
    sh = gc.open_by_key(SHEET_ID)
    ws = None
    for w in sh.worksheets():
        if str(w.id) == GID:
            ws = w
            break
    if not ws:
        raise Exception("Sheet not found")
    return ws, ws.get_all_values()

if __name__ == "__main__":
    print("Start: emisja_sheets_sync.py")
    vse_token = get_jwt_token()
    
    print("Fetching Google Sheets data (Emisja)...")
    ws, rows = get_sheet_data()
    if not rows:
        print("Pusty arkusz.")
        sys.exit(0)
        
    headers = [str(h).strip().lower() for h in rows[0]]
    
    idx_yt_link = headers.index("yt url") if "yt url" in headers else 5
    idx_yt_id = headers.index("youtube id") if "youtube id" in headers else 1
    idx_title = headers.index("tytuł") if "tytuł" in headers else 2
    idx_status = headers.index("status") if "status" in headers else 9
    idx_date = headers.index("data emisji") if "data emisji" in headers else 7
    idx_img = next((i for i, h in enumerate(headers) if h == "obrazek główny" or h == "ścieżka do obrazka" or "obrazek" in h and "dodatkowe" not in h), None)
    idx_img_add = next((i for i, h in enumerate(headers) if "obrazki dodatkowe" in h), None)
    
    for row_idx, row in enumerate(rows):
        if row_idx == 0:
            continue
            
        while len(row) < len(headers):
            row.append("")
            
        status = row[idx_status].strip().lower()
        if status in ["opublikowany", "zaplanowany"]:
            continue
            
        yt_link = row[idx_yt_link].strip()
        yt_id = row[idx_yt_id].strip()
        
        if not yt_id and yt_link:
            if "youtu.be/" in yt_link:
                yt_id = yt_link.split("youtu.be/")[1].split("?")[0]
            elif "watch?v=" in yt_link:
                yt_id = yt_link.split("watch?v=")[1].split("&")[0]
                
        if not yt_id:
            continue
            
        title = row[idx_title].strip() or f"Emisja {yt_id}"
        date_str = row[idx_date].strip()
        
        pub_at = ""
        if date_str:
            try:
                # np. 2026-09-08
                if len(date_str.split("-")) == 3:
                    dt = datetime.strptime(date_str, "%Y-%m-%d")
                elif len(date_str.split(".")) == 3:
                    dt = datetime.strptime(date_str, "%d.%m.%Y")
                else:
                    dt = datetime.strptime(date_str, "%d.%m")
                    dt = dt.replace(year=datetime.now().year)
                pub_at = dt.strftime("%Y-%m-%dT00:00:00+02:00")
            except Exception:
                pass
                
        print(f"\n{'='*60}\nProcessing row {row_idx+1}: {title}\n{'='*60}")
        
        schema = step_generate_yt(yt_id, title, vse_token)
        if not schema:
            print("  Skipping: schema generation failed.")
            continue
            
        post_id = step_inject_wp(schema, pub_at, vse_token, yt_id)
        if post_id:
            if idx_img is not None and len(row) > idx_img:
                img_path = row[idx_img].strip()
                if img_path:
                    step_upload_image(post_id, img_path)
                    
            if idx_img_add is not None and len(row) > idx_img_add:
                img_add_str = row[idx_img_add].strip()
                if img_add_str:
                    for img in img_add_str.split(','):
                        img_path = img.strip()
                        if img_path:
                            step_upload_image(post_id, img_path)
                
        try:
            ws.update_cell(row_idx + 1, idx_status + 1, "Zaplanowany")
            print("  [OK] Zaktualizowano status w Excelu")
        except Exception as e:
            print(f"  [ERROR] Sheet update failed: {e}")
            
        time.sleep(3)
