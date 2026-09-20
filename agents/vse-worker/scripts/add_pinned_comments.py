#!/usr/bin/env python3
"""
add_pinned_comments.py — dodaje pinned comments do opublikowanych shortów

Czyta /tmp/shorts_schedule_results.json (wynik prawy_shorts_schedule.py).
Dla każdego shorta: sprawdza czy jest publiczny, dodaje pinned comment.
Bezpieczne do wielokrotnego uruchomienia.

Uruchomienie wewnatrz kontenera:
  docker exec -w /app vse-api python3 add_pinned_comments.py [YYYY-MM-DD]

  Bez argumentu: wszystkie shorty z results JSON
  Z data:        tylko shorty z publishAt na ten dzien

Autor: biblia-worker | media-dispatch 20.09.2026
"""
import sys, json, asyncio, datetime, os
from jose import jwt
from sqlalchemy.future import select
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

from api.db import AsyncSessionLocal
from api.models.youtube_channel import YouTubeChannel
from api.core.youtube_publish import _build_credentials

RESULTS_FILE = "/tmp/shorts_schedule_results.json"

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
                channels.append({"title": ch.title, "creds": creds})
            except Exception as e:
                print(f"[WARN] {ch.title}: {e}")
    return channels

def is_video_public(channels, video_id):
    for ch in channels:
        try:
            youtube = build("youtube", "v3", credentials=ch["creds"])
            resp = youtube.videos().list(part="status", id=video_id).execute()
            items = resp.get("items", [])
            if items:
                status = items[0].get("status", {}).get("privacyStatus", "")
                print(f"  [STATUS] {video_id}: privacyStatus={status}")
                return status == "public"
        except Exception as e:
            print(f"  [WARN] status check {video_id}: {e}")
    return False

def add_pinned_comment(channels, video_id, comment_text):
    for ch in channels:
        try:
            youtube = build("youtube", "v3", credentials=ch["creds"])
            body = {
                "snippet": {
                    "videoId": video_id,
                    "topLevelComment": {
                        "snippet": {"textOriginal": comment_text}
                    }
                }
            }
            res = youtube.commentThreads().insert(part="snippet", body=body).execute()
            comment_id = res.get("id")
            print(f"  [OK] Comment posted: id={comment_id} ({ch['title']})")
            return True, comment_id
        except Exception as e:
            print(f"  [ERROR] {ch['title']}: {e}")
    return False, None

async def main():
    date_filter = sys.argv[1] if len(sys.argv) > 1 else None
    print(f"=== add_pinned_comments.py | filtr={date_filter or 'wszystkie'} ===")

    if not os.path.exists(RESULTS_FILE):
        print(f"[ERROR] Brak pliku: {RESULTS_FILE}")
        return

    with open(RESULTS_FILE, "r", encoding="utf-8") as f:
        results = json.load(f)

    if date_filter:
        results = [r for r in results if r.get("publish_at", "").startswith(date_filter)]
        print(f"[FILTER] Dzien {date_filter}: {len(results)} shortow")

    channels = await get_yt_channels()
    print(f"[AUTH] Kanaly: {[c['title'] for c in channels]}")

    summary = []
    for r in results:
        yt_id   = r["youtube_id"]
        comment = r.get("pinned_comment", "")
        slot    = r.get("slot", "")
        title   = (r.get("optimized_title") or "")[:40]
        print(f"\n--- {yt_id} | {slot} | {title} ---")
        if not comment:
            print(f"  [SKIP] Brak pinned_comment")
            summary.append({"id": yt_id, "status": "skip_no_comment"})
            continue
        if not is_video_public(channels, yt_id):
            print(f"  [SKIP] Nie publiczne: {yt_id}")
            summary.append({"id": yt_id, "status": "skip_not_public"})
            continue
        ok, cid = add_pinned_comment(channels, yt_id, comment)
        summary.append({"id": yt_id, "slot": slot, "status": "ok" if ok else "fail", "comment_id": cid})

    print("\n=== SUMMARY ===")
    for s in summary:
        icon = "OK" if s["status"] == "ok" else "SKIP" if "skip" in s["status"] else "FAIL"
        print(f"  [{icon}] {s['id']} | {s.get('slot','')} | {s['status']}")

if __name__ == "__main__":
    asyncio.run(main())
