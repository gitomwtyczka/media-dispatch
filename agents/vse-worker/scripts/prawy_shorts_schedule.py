#!/usr/bin/env python3
"""
prawy_shorts_schedule.py — Scheduling 9 shortów Prawy TV + VSE describe

Uruchomienie wewnątrz kontenera vse-api:
  scp prawy_shorts_schedule.py ubuntu@147.224.162.100:/tmp/
  ssh ubuntu@... "docker cp /tmp/prawy_shorts_schedule.py vse-api:/app/ && docker exec -w /app vse-api python3 prawy_shorts_schedule.py"

Co robi:
  1. /v1/shorts/describe → optimized_title, description, hashtags, pinned_comment
  2. YouTube videos().update() → aktualizacja metadanych
  3. YouTube videos().update() → privacyStatus=private + publishAt (scheduling)
  4. pinned_comment zapisany do JSON (nie dodawany — video jeszcze niepubliczne)

Autor: biblia-worker | media-dispatch 20.09.2026
"""

import os
import re
import json
import time
import datetime
import requests
import asyncio
from jose import jwt
from sqlalchemy.future import select
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

from api.db import AsyncSessionLocal
from api.models.youtube_channel import YouTubeChannel
from api.core.youtube_publish import _build_credentials

# ===== CONFIG =====
SHORTS = [
    {"id": "jr8xmftcedQ", "slot": "21.09 09:00 CEST", "publishAt": "2026-09-21T09:00:00+02:00"},
    {"id": "m-QXJIeUhxY",  "slot": "21.09 15:00 CEST", "publishAt": "2026-09-21T15:00:00+02:00"},
    {"id": "s0vKdT_rEB0",  "slot": "21.09 21:00 CEST", "publishAt": "2026-09-21T21:00:00+02:00"},
    {"id": "vaTc9g1vntI",  "slot": "22.09 09:00 CEST", "publishAt": "2026-09-22T09:00:00+02:00"},
    {"id": "K1J_UXyrpt0",  "slot": "22.09 15:00 CEST", "publishAt": "2026-09-22T15:00:00+02:00"},
    {"id": "XZNkaPPBuR8",  "slot": "22.09 21:00 CEST", "publishAt": "2026-09-22T21:00:00+02:00"},
    {"id": "FTfqWno1ZsQ",  "slot": "23.09 09:00 CEST", "publishAt": "2026-09-23T09:00:00+02:00"},
    {"id": "wdR0wTQd7kI",  "slot": "23.09 15:00 CEST", "publishAt": "2026-09-23T15:00:00+02:00"},
    {"id": "YK1E9InVfu0",  "slot": "23.09 21:00 CEST", "publishAt": "2026-09-23T21:00:00+02:00"},
]

PORTAL_ID = "2b047d7d-15a1-4d2f-8463-f89c2275bb73"
VSE_BASE  = "http://localhost:8085"

# ===== AUTH =====

def get_jwt():
    secret = os.environ.get('JWT_SECRET_KEY', '')
    payload = {
        'sub': '4b97ab0c-98ee-46c6-9be8-d86adc4cb38a',
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }
    return jwt.encode(payload, secret, algorithm='HS256')

async def get_yt_channels():
    channels = []
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(YouTubeChannel).where(YouTubeChannel.is_active == True))
        for ch in res.scalars().all():
            try:
                creds = _build_credentials(ch)
                creds.refresh(Request())
                channels.append({
                    "id": str(ch.id),
                    "channel_id": ch.youtube_channel_id,
                    "title": ch.title,
                    "token": creds.token,
                    "creds": creds
                })
            except Exception as e:
                print(f"[WARN] Channel {ch.title} token failed: {e}")
    return channels

# ===== VTT =====

def ensure_vtt_exists(channels, video_id):
    vtt_path = f"/tmp/{video_id}.vtt"
    if os.path.exists(vtt_path) and os.path.getsize(vtt_path) > 0:
        return True
    for ch in channels:
        try:
            youtube = build("youtube", "v3", credentials=ch["creds"])
            c_resp = youtube.captions().list(part="snippet", videoId=video_id).execute()
            items = c_resp.get("items", [])
            if not items:
                continue
            cap_id = items[0]["id"]
            req = youtube.captions().download(id=cap_id, tfmt="vtt")
            content = req.execute()
            with open(vtt_path, "wb") as f:
                f.write(content)
            print(f"[VTT] Downloaded for {video_id} ({len(content)} bytes)")
            return True
        except Exception as e:
            print(f"[VTT] Could not download for {video_id} from {ch['title']}: {e}")
    return False

# ===== VSE DESCRIBE =====

def describe_short(token, youtube_id):
    url = f"{VSE_BASE}/v1/shorts/describe"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"youtube_id": youtube_id, "portal_id": PORTAL_ID}
    print(f"[DESC] {url} for {youtube_id}...")
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        print(f"[DESC] Status {resp.status_code}: {resp.text[:300]}")
        if resp.status_code == 200:
            return resp.json()
        return {"error": f"HTTP {resp.status_code}: {resp.text}"}
    except Exception as e:
        return {"error": str(e)}

# ===== YOUTUBE UPDATE =====

def deduplicate_description(desc: str) -> str:
    seen = set()
    pattern = re.compile(r'#[A-Za-z0-9_ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]+')
    lines = desc.split('\n')
    new_lines = []
    for line in lines:
        def repl(m):
            tag = m.group(0)
            tag_lower = tag.lower()
            if tag_lower in seen:
                return ""
            seen.add(tag_lower)
            return tag
        new_line = pattern.sub(repl, line)
        new_line = re.sub(r'[ \t]+', ' ', new_line).strip()
        new_lines.append(new_line)
    res = '\n'.join(new_lines)
    return re.sub(r'\n{3,}', '\n\n', res).strip()

def update_and_schedule_youtube(channels, video_id, title, description, hashtags, publish_at):
    """Łączy update metadanych + scheduling w jednym wywołaniu."""
    # Przygotuj opis z hashtagami
    if isinstance(hashtags, list):
        tags_formatted = [h if h.startswith("#") else f"#{h}" for h in hashtags]
    else:
        tags_formatted = []
    desc_lower = description.lower()
    new_tags = [h for h in tags_formatted if h.lower() not in desc_lower]
    full_desc = deduplicate_description(
        description + ("\n\n" + " ".join(new_tags) if new_tags else "")
    )

    print(f"\n--- Scheduling YT Short {video_id} ---")
    print(f"Title: {title}")
    print(f"PublishAt: {publish_at}")
    print(f"Description:\n{full_desc[:200]}...")

    for ch in channels:
        try:
            youtube = build("youtube", "v3", credentials=ch["creds"])
            v_resp = youtube.videos().list(part="snippet,status", id=video_id).execute()
            items = v_resp.get("items", [])
            if not items:
                continue

            snippet = items[0]["snippet"]
            snippet["title"] = title[:100]
            snippet["description"] = full_desc

            # Scheduling: privacyStatus=private + publishAt
            new_status = {
                "privacyStatus": "private",
                "publishAt": publish_at  # RFC3339, np. 2026-09-21T09:00:00+02:00
            }

            res = youtube.videos().update(
                part="snippet,status",
                body={"id": video_id, "snippet": snippet, "status": new_status}
            ).execute()
            print(f"[YT] OK: {video_id} scheduled → {publish_at} ({ch['title']})")
            return True, full_desc
        except Exception as e:
            print(f"[YT] ERROR on {ch['title']}: {e}")
    return False, full_desc

# ===== MAIN =====

async def main():
    token = get_jwt()
    print(f"[AUTH] JWT OK: {token[:20]}...")
    channels = await get_yt_channels()
    print(f"[AUTH] YT channels: {[c['title'] for c in channels]}")

    results = []
    max_retries = 10

    for item in SHORTS:
        yt_id      = item["id"]
        slot       = item["slot"]
        publish_at = item["publishAt"]

        print(f"\n{'='*50}")
        print(f"Short: {yt_id} | {slot}")
        print(f"{'='*50}")

        # Ensure VTT (dla ASR)
        ensure_vtt_exists(channels, yt_id)

        # Describe z retry
        desc_res = None
        for attempt in range(1, max_retries + 1):
            desc_res = describe_short(token, yt_id)
            has_title = bool(desc_res.get("optimized_title") or desc_res.get("title"))
            if desc_res.get("error") or not has_title:
                print(f"[RETRY] Attempt {attempt}/{max_retries} — waiting 60s...")
                if attempt < max_retries:
                    time.sleep(60)
                    token = get_jwt()  # Odśwież token
                    continue
            else:
                print(f"[OK] describe sukces na próbie {attempt}")
                break

        opt_title      = desc_res.get("optimized_title") or desc_res.get("title") or yt_id
        desc           = desc_res.get("description") or ""
        hashtags       = desc_res.get("hashtags") or []
        pinned_comment = desc_res.get("pinned_comment") or ""
        related_vid    = desc_res.get("related_video_id") or ""

        # Update + schedule
        yt_ok, full_desc = update_and_schedule_youtube(
            channels, yt_id, opt_title, desc, hashtags, publish_at
        )

        results.append({
            "youtube_id": yt_id,
            "slot": slot,
            "publish_at": publish_at,
            "optimized_title": opt_title,
            "description": full_desc,
            "hashtags": hashtags,
            "pinned_comment": pinned_comment,  # Do dodania po publikacji
            "related_video_id": related_vid,
            "yt_scheduled": yt_ok,
            "vse_raw": desc_res
        })
        time.sleep(2)

    # Zapis wyników
    out_path = "/tmp/shorts_schedule_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n\n=== SUMMARY ===")
    for r in results:
        icon = "✅" if r["yt_scheduled"] else "❌"
        print(f"  {icon} {r['youtube_id']} | {r['slot']} | {r['optimized_title'][:45]}")
    print(f"\nWyniki: {out_path}")
    print("\nNOTE: pinned_comment nie dodany — video scheduled (prywatne). Dodaj po publikacji.")

if __name__ == "__main__":
    asyncio.run(main())
