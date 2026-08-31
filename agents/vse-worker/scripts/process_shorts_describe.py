#!/usr/bin/env python3
"""
process_shorts_describe.py — media-dispatch / VSE Short Machine integration

Przetwarzanie 8 shortów przez endpoint POST /v1/shorts/describe:
- Generowanie JWT tokenu z bazy/ENV VSE
- Pobranie i odświeżenie tokenów YouTube z bazy danych VSE
- POST /v1/shorts/describe z youtube_id i portal_id
- Aktualizacja metadanych na YouTube (optimized_title, description, hashtags)
- Dodanie przypiętego komentarza (pinned_comment)
- Zapis wyników do /tmp/shorts_described.json

Uruchomienie wewnątrz kontenera vse-api:
  docker cp process_shorts_describe.py vse-api:/app/process_shorts_describe.py
  docker exec -w /app vse-api python3 /app/process_shorts_describe.py
"""

import os
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

SHORTS = [
    {"id": "ioObSLpRGc4", "slot": "01.09 07:00 (PRIORYTET #1)"},
    {"id": "FtQNSzHtQ0s", "slot": "01.09 12:00 (PRIORYTET #2)"},
    {"id": "9tjEXGE5sXg", "slot": "01.09 18:00 (PRIORYTET #3)"},
    {"id": "mw6A9CZ6DuM", "slot": "private"},
    {"id": "mTyr64ygkJU", "slot": "private"},
    {"id": "8nbA6YSZAVQ", "slot": "private"},
    {"id": "slA15REfjpU", "slot": "private"},
    {"id": "lX2vvs8E-AY", "slot": "private"}
]

PORTAL_ID = "2b047d7d-15a1-4d2f-8463-f89c2275bb73"
VSE_BASE = "http://localhost:8085"

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
                print(f"[WARN] Failed to refresh creds for channel {ch.title}: {e}")
    return channels

def describe_short(token, youtube_id):
    url = f"{VSE_BASE}/v1/shorts/describe"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "youtube_id": youtube_id,
        "portal_id": PORTAL_ID
    }
    print(f"Calling {url} for {youtube_id}...")
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        print(f"Status {resp.status_code}: {resp.text[:300]}")
        if resp.status_code == 200:
            return resp.json()
        else:
            return {"error": f"HTTP {resp.status_code}: {resp.text}"}
    except Exception as e:
        print(f"Exception calling describe: {e}")
        return {"error": str(e)}

def update_youtube_video(channels, video_id, title, description, hashtags):
    tags_formatted = []
    if isinstance(hashtags, list):
        for h in hashtags:
            h_clean = h.strip()
            if not h_clean.startswith("#"):
                h_clean = f"#{h_clean}"
            tags_formatted.append(h_clean)
        tags_str = " ".join(tags_formatted)
    elif isinstance(hashtags, str):
        tags_str = hashtags
    else:
        tags_str = ""

    full_description = description
    if tags_str and tags_str not in full_description:
        full_description = f"{full_description}\n\n{tags_str}"

    print(f"\n--- Updating YT Video {video_id} ---")
    print(f"Title: {title}")
    print(f"Description:\n{full_description}\n")

    for ch in channels:
        try:
            youtube = build("youtube", "v3", credentials=ch["creds"])
            v_resp = youtube.videos().list(part="snippet,status", id=video_id).execute()
            items = v_resp.get("items", [])
            if not items:
                continue
            
            item = items[0]
            snippet = item["snippet"]
            status = item.get("status", {})

            # Update snippet title and description
            snippet["title"] = title[:100]
            snippet["description"] = full_description

            update_body = {
                "id": video_id,
                "snippet": snippet
            }
            # Keep status unchanged (do NOT alter publishAt or privacyStatus)
            if status:
                update_body["status"] = status

            res = youtube.videos().update(part="snippet,status", body=update_body).execute()
            print(f"Successfully updated video {video_id} on channel {ch['title']}")
            return True, f"Updated on {ch['title']}"
        except Exception as e:
            print(f"Error updating video on channel {ch['title']}: {e}")
    return False, "Failed on all channels"

def add_pinned_comment(channels, video_id, comment_text):
    if not comment_text:
        return False, "No comment text"
    
    print(f"\n--- Adding Pinned Comment for {video_id} ---")
    print(f"Comment text: {comment_text}")

    for ch in channels:
        try:
            youtube = build("youtube", "v3", credentials=ch["creds"])
            body = {
                "snippet": {
                    "videoId": video_id,
                    "topLevelComment": {
                        "snippet": {
                            "textOriginal": comment_text
                        }
                    }
                }
            }
            res = youtube.commentThreads().insert(part="snippet", body=body).execute()
            comment_id = res.get("id")
            print(f"Comment posted (ID: {comment_id}) on channel {ch['title']}")
            return True, f"Comment posted (ID: {comment_id})"
        except Exception as e:
            print(f"Error posting comment on channel {ch['title']}: {e}")
            return False, str(e)
    return False, "Failed on all channels"

async def main():
    token = get_jwt()
    print(f"Generated JWT token: {token[:20]}...")
    channels = await get_yt_channels()
    print(f"Active YT channels: {[c['title'] for c in channels]}")

    results = []

    for item in SHORTS:
        yt_id = item["id"]
        slot = item["slot"]
        print(f"\n==========================================")
        print(f"Processing Short: {yt_id} ({slot})")
        print(f"==========================================")

        desc_res = describe_short(token, yt_id)
        
        opt_title = desc_res.get("optimized_title") or desc_res.get("title") or ""
        desc = desc_res.get("description") or ""
        hashtags = desc_res.get("hashtags") or []
        pinned_comment = desc_res.get("pinned_comment") or ""

        yt_update_ok = False
        yt_update_msg = ""
        comment_ok = False
        comment_msg = ""

        if opt_title:
            yt_update_ok, yt_update_msg = update_youtube_video(channels, yt_id, opt_title, desc, hashtags)
        else:
            yt_update_msg = f"No title in VSE response: {desc_res}"

        if pinned_comment:
            comment_ok, comment_msg = add_pinned_comment(channels, yt_id, pinned_comment)
        else:
            comment_msg = f"No pinned_comment in VSE response"

        results.append({
            "youtube_id": yt_id,
            "slot": slot,
            "vse_response": desc_res,
            "optimized_title": opt_title,
            "description": desc,
            "hashtags": hashtags,
            "pinned_comment": pinned_comment,
            "yt_updated": yt_update_ok,
            "yt_update_msg": yt_update_msg,
            "comment_added": comment_ok,
            "comment_msg": comment_msg
        })

    with open("/tmp/shorts_described.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n\nAll shorts processed! Saved to /tmp/shorts_described.json")

if __name__ == "__main__":
    asyncio.run(main())
