#!/usr/bin/env python3
"""
Uruchamiany WEWNATRZ vse-api kontenera:
  scp yt_desc_fix.py ubuntu@VPS:/tmp/
  ssh ubuntu@VPS docker cp /tmp/yt_desc_fix.py vse-api:/app/
  ssh ubuntu@VPS docker exec -w /app vse-api python3 yt_desc_fix.py

Aktualizuje opisy YT dla filmów z transcript_jobs schema_data.
Używa tokenu Tomasz Brzozowski (zarządza kanałami Prawy przez konto osobiste).
"""
import asyncio, json
from sqlalchemy.future import select
from sqlalchemy import text

# EDYTUJ TEN SLOWNIK przed uruchomieniem
FILMS = [
    {"yt_id": "EWkRL1sEqQE", "wp_url": "https://prawy.pl/?p=126276", "title": "Pluzanski Popek Wolyn 1"},
    {"yt_id": "s6qif3Ed57E", "wp_url": "https://prawy.pl/?p=126295", "title": "Pluzanski Pietrzak"},
]
CHANNEL_TITLE = "Tomasz Brzozowski"  # konto zarzadzajace kanalami Prawy

async def main():
    from api.db import AsyncSessionLocal
    from api.models.youtube_channel import YouTubeChannel
    from api.core.youtube_publish import _build_credentials
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(YouTubeChannel).where(YouTubeChannel.title == CHANNEL_TITLE)
        )
        ch = res.scalar_one_or_none()
        if not ch:
            print(f"[FATAL] Channel '{CHANNEL_TITLE}' not found!")
            return

        print(f"[channel] Using: {ch.title}")
        creds = _build_credentials(ch)
        creds.refresh(Request())
        print(f"[oauth] OK")

        youtube = build("youtube", "v3", credentials=creds)

        for film in FILMS:
            print(f"\n=== {film['title']} ({film['yt_id']}) ===")

            row = (await db.execute(text(
                f"SELECT schema_data FROM transcript_jobs "
                f"WHERE video_url LIKE '%{film['yt_id']}%' "
                f"ORDER BY created_at DESC LIMIT 1"
            ))).fetchone()

            if not row or not row[0]:
                print(f"[skip] No schema_data in DB")
                continue

            schema = row[0]

            # Buduj opis
            lead = schema.get("lead") or ""
            raw_chapters = schema.get("chapters") or []
            chapter_lines = []
            for c in raw_chapters:
                if isinstance(c, dict):
                    t = c.get("time") or c.get("timestamp") or ""
                    ti = c.get("title") or c.get("name") or ""
                    chapter_lines.append(f"{t} {ti}".strip())
                elif isinstance(c, str):
                    chapter_lines.append(c)
            chapters_str = "\n".join(chapter_lines)
            tags = schema.get("tags") or []
            hashtags_str = " ".join(f"#{t}" if not str(t).startswith("#") else str(t) for t in tags)

            parts = [p for p in [lead, chapters_str, hashtags_str,
                                  f"Czytaj wiecej: {film['wp_url']}"] if p]
            desc = "\n\n".join(parts)
            print(f"[desc] {len(desc)} chars: {desc[:150]}...")

            v_resp = youtube.videos().list(part="snippet,status", id=film['yt_id']).execute()
            items = v_resp.get("items", [])
            if not items:
                print(f"[skip] Video not accessible")
                continue

            snippet = items[0]["snippet"]
            status_body = items[0].get("status", {})
            snippet["description"] = desc

            upd = youtube.videos().update(
                part="snippet,status",
                body={"id": film['yt_id'], "snippet": snippet, "status": status_body}
            ).execute()
            print(f"[yt] UPDATED OK ({len(upd['snippet'].get('description',''))} chars)")

asyncio.run(main())