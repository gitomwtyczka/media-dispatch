#!/usr/bin/env python3
"""
prawy_standard_pipeline.py — Pipeline B: Prawy TV / Studio Prawy (kanał z auto-napisami YT)

Wersja 2.0 (zgodna z konstytucją VSE v2):
- llm_provider: claude (nie gemini)
- publication_type: full_analysis (nie film)
- portal_id: 2b047d7d-15a1-4d2f-8463-f89c2275bb73 (UUID prawy.pl)
- YT token: przez SSH + _build_credentials (z bazy VSE)

ARCHITEKTURA:
  Kanały z auto-captions PL na YouTube → Whisper NIE jest potrzebny.

  Krok 1: POST /v1/generate z URL YouTube → pełne SEO (thumbnail, VideoObject, embed)
  Krok 2: POST /v1/inject → WP post (publish / future)
  Krok 3: videos.update → opis i tytuł YouTube (z schema_data)
"""
import json, time, subprocess, requests
from typing import Optional

# ===== CONFIG =====
VSE_BASE = "https://vse.impresjapr.pl"
SSH_KEY = r"C:\Users\tomas2\.ssh\oracle-crimson.key"
VPS = "ubuntu@147.224.162.100"
PORTAL_ID = "2b047d7d-15a1-4d2f-8463-f89c2275bb73"  # prawy.pl UUID

def get_jwt_token() -> str:
    print("[0] JWT token przez SSH...")
    code = (
        "import os, datetime; "
        "from jose import jwt; "
        "s = os.environ.get('JWT_SECRET_KEY', ''); "
        "p = {'sub': '4b97ab0c-98ee-46c6-9be8-d86adc4cb38a', 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)}; "
        "print(jwt.encode(p, s, algorithm='HS256'))"
    )
    cmd = [
        "ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no", VPS,
        f"docker exec vse-api python3 -c \"{code}\""
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    token = r.stdout.strip()
    if not token:
        raise RuntimeError(f"JWT failed: {r.stderr[:200]}")
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
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    lines = [l for l in r.stdout.strip().split('\n') if l.startswith('[')]
    if not lines:
        raise RuntimeError(f"YT tokens failed: {r.stderr[:200]}")
    return json.loads(lines[-1])

def vsh(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}

def step1_generate(yt_url: str, vse_token: str, title: Optional[str] = None) -> Optional[dict]:
    """YouTube URL → /v1/generate → pełne SEO z thumbnail i VideoObject."""
    print(f"  [1] VSE generate: {yt_url}")
    payload = {
        "video_url": yt_url,
        "publication_type": "full_analysis",
        "portal_id": PORTAL_ID,
        "lang": "pl",
        "llm_provider": "claude",
    }
    if title:
        payload["post_title"] = title
    r = requests.post(f"{VSE_BASE}/v1/generate", headers=vsh(vse_token), json=payload, timeout=360)
    if r.status_code != 200:
        print(f"  [1] ERROR {r.status_code}: {r.text[:200]}")
        return None
    d = r.json()
    print(f"  [1] OK status={d.get('status')}")
    return d.get("schema_data")

def step2_inject(schema: dict, yt_url: str, vse_token: str, post_status: str = "publish") -> Optional[int]:
    """schema → /v1/inject → WP post."""
    print(f"  [2] Inject to WP, status={post_status}")
    r = requests.post(f"{VSE_BASE}/v1/inject", headers=vsh(vse_token), json={
        "video_url": yt_url,
        "schema_data": schema,
        "portal_id": PORTAL_ID,
        "post_status": post_status
    }, timeout=120)
    if r.status_code != 200:
        print(f"  [2] ERROR {r.status_code}: {r.text[:200]}")
        return None
    resp = r.json()
    pid = resp.get("wp_post_id") or resp.get("post_id")
    print(f"  [2] WP post: {pid} ({resp.get('post_url')})")
    return pid

def step3_update_yt(video_id: str, title: str, description: str, yt_tokens: list) -> bool:
    """Update YouTube: tytuł SEO + opis + public."""
    print(f"  [3] YT update: {video_id}")
    from googleapiclient.discovery import build
    from google.oauth2.credentials import Credentials

    for t_info in yt_tokens:
        try:
            creds = Credentials(t_info["token"])
            youtube = build("youtube", "v3", credentials=creds)
            v_resp = youtube.videos().list(part="snippet,status", id=video_id).execute()
            items = v_resp.get("items", [])
            if not items:
                continue
            snippet = items[0]["snippet"]
            snippet["title"] = title[:100]
            if description:
                snippet["description"] = description
            youtube.videos().update(
                part="snippet,status",
                body={"id": video_id, "snippet": snippet, "status": {"privacyStatus": "public"}}
            ).execute()
            print(f"  [3] OK ({t_info['title']})")
            return True
        except Exception as e:
            print(f"  [3] {t_info['title']}: {e}")
    return False
