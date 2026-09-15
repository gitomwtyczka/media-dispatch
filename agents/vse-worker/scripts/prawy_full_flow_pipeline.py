import subprocess, json, requests
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import json as _json

SSH_KEY = r"C:\Users\tomas2\.ssh\oracle-crimson.key"
VPS = "ubuntu@147.224.162.100"
VSE_BASE = "https://vse.impresjapr.pl"
PORTAL_ID = "2b047d7d-15a1-4d2f-8463-f89c2275bb73"

def get_jwt():
    code = (
        "import os, datetime; "
        "from jose import jwt; "
        "s = os.environ.get('JWT_SECRET_KEY', ''); "
        "p = {'sub': '4b97ab0c-98ee-46c6-9be8-d86adc4cb38a', 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)}; "
        "print(jwt.encode(p, s, algorithm='HS256'))"
    )
    cmd = ["ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no", VPS,
           f"docker exec vse-api python3 -c \"{code}\""]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    token = r.stdout.strip()
    if not token:
        raise RuntimeError(f"JWT failed: {r.stderr[:200]}")
    return token

def get_yt_tokens():
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
    cmd = ["ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no", VPS,
           f"docker exec -w /app vse-api python3 -c {subprocess.list2cmdline([code])}"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    lines = [l for l in r.stdout.strip().split('\n') if l.startswith('[')]
    if not lines:
        raise RuntimeError(f"YT tokens failed: {r.stderr[:200]}")
    return json.loads(lines[-1])

def step_generate(yt_url, vse_token, title=None):
    payload = {
        "video_url": yt_url,
        "publication_type": "full_analysis",
        "portal_id": PORTAL_ID,
        "lang": "pl",
        "llm_provider": "claude"
    }
    if title:
        payload["post_title"] = title
    r = requests.post(f"{VSE_BASE}/v1/generate",
                      headers={"Authorization": f"Bearer {vse_token}"},
                      json=payload, timeout=360)
    print(f"[generate] {r.status_code}: {r.text[:300]}")
    if r.status_code != 200:
        return None
    return r.json().get("schema_data")

def step_inject(schema, yt_url, vse_token):
    r = requests.post(f"{VSE_BASE}/v1/inject",
                      headers={"Authorization": f"Bearer {vse_token}"},
                      json={
                          "video_url": yt_url,
                          "schema_data": schema,
                          "portal_id": PORTAL_ID,
                          "post_status": "draft"
                      }, timeout=120)
    print(f"[inject] {r.status_code}: {r.text[:300]}")
    if r.status_code != 200:
        return None
    resp = r.json()
    return resp.get("wp_post_id") or resp.get("post_id")

def step_update_yt(video_id, schema, yt_tokens):
    title = schema.get("title") or schema.get("post_title") or ""
    desc = schema.get("description") or schema.get("meta_description") or ""
    if not desc and schema.get("seo_data"):
        desc = schema["seo_data"].get("description", "")
    
    for t_info in yt_tokens:
        try:
            creds = Credentials(t_info["token"])
            youtube = build("youtube", "v3", credentials=creds)
            v_resp = youtube.videos().list(part="snippet,status", id=video_id).execute()
            items = v_resp.get("items", [])
            if not items:
                continue
            snippet = items[0]["snippet"]
            status_body = items[0].get("status", {})
            if title:
                snippet["title"] = title[:100]
            if desc:
                snippet["description"] = desc
            youtube.videos().update(
                part="snippet,status",
                body={"id": video_id, "snippet": snippet, "status": status_body}
            ).execute()
            print(f"[yt_update] OK for {video_id} via {t_info['title']}")
            return True
        except Exception as e:
            print(f"[yt_update] {t_info['title']}: {e}")
    return False

def main():
    FILMS = [
        {"yt_id": "EWkRL1sEqQE", "title": "Płużański Popek Wołyń 1"},
        {"yt_id": "s6qif3Ed57E", "title": "Płużański Pietrzak"},
    ]

    results = []
    vse_token = get_jwt()
    yt_tokens = get_yt_tokens()
    print(f"YT channels: {[t['title'] for t in yt_tokens]}")

    for film in FILMS:
        yt_url = f"https://www.youtube.com/watch?v={film['yt_id']}"
        print(f"\n=== {film['title']} ===")
        
        schema = step_generate(yt_url, vse_token, film["title"])
        if not schema:
            results.append({"film": film["title"], "status": "FAILED", "step": "generate"})
            continue
        
        wp_post_id = step_inject(schema, yt_url, vse_token)
        yt_ok = step_update_yt(film["yt_id"], schema, yt_tokens)
        
        results.append({
            "film": film["title"],
            "yt_id": film["yt_id"],
            "wp_post_id": wp_post_id,
            "yt_updated": yt_ok,
            "status": "OK" if wp_post_id else "PARTIAL"
        })
        print(f"  WP post: {wp_post_id}, YT: {yt_ok}")

    with open(r"C:\Users\tomas2\.gemini\antigravity\brain\phase1_results.json", "w", encoding="utf-8") as f:
        _json.dump(results, f, ensure_ascii=False, indent=2)
    print("\nResults saved to phase1_results.json")
    print(_json.dumps(results, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()