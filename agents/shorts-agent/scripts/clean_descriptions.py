"""
agents/shorts-agent/scripts/clean_descriptions.py

Czyszczenie opisów 23 shortów z placeholdera @naszkanal → @portalprawypl.
Uruchom wewnątrz kontenera vse-api:
  docker cp agents/shorts-agent/scripts/clean_descriptions.py vse-api:/app/clean_descriptions.py
  docker exec -w /app vse-api python3 /app/clean_descriptions.py

Wymagania:
- Aktywny token OAuth dla kanału Studio Prawy_PL (prawypl5@gmail.com)
- Limit YouTube API: ~23 pkt (GET) + 23x50 pkt (PUT) = 1173 pkt
- Quota resetuje się o 09:00 CEST
"""

import asyncio
import json
import re

from api.db import AsyncSessionLocal
from api.models.youtube_channel import YouTubeChannel
from api.core.youtube_publish import _build_credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from sqlalchemy.future import select

ALL_SHORTS = [
    "vykiY72rCLE", "ZpfLMoEcHJU", "Ud39NRwg6bc",
    "tAvFCPB5edo", "NSgYkAqMSWU", "otu-Wl0hSAk", "pnBGXd3-fpQ",
    "wpijwznWNbQ", "9Tkv8ue2l-0", "8U31DNanCxM", "9Djd9bAalQg", "Ub6IU_qzzSA",
    "fdNWzWOrI94", "7PnGnQeZGow", "0Q5EzAHn9i4", "etW9qE9O2LQ",
    "DuWGHfRmkXA", "kqby7mJZhuA", "GLRHMx-A-lE", "VpOQRrHWR0Q",
    "MplQERzDdQk", "jT4xLEC-_fw", "hde4weDkpJU"
]

CORRECT_HANDLE = "@portalprawypl"


async def get_youtube_service():
    """Pobiera usługę YouTube z aktywnym tokenem OAuth z bazy VSE."""
    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(YouTubeChannel).where(YouTubeChannel.is_active == True)
        )
        for ch in res.scalars().all():
            try:
                creds = _build_credentials(ch)
                creds.refresh(Request())
                print(f"[OK] Token odswiezony dla kanału: {ch.title}")
                return build("youtube", "v3", credentials=creds)
            except Exception as e:
                print(f"[SKIP] {ch.title}: {e}")
    raise RuntimeError("Brak aktywnych tokenów YouTube OAuth w bazie VSE")


def clean_description(desc: str) -> str:
    """Zamienia wszystkie warianty @naszkanal na @portalprawypl i normalizuje CTA."""
    # Zamień wszystkie warianty @naszkanal (case-insensitive)
    cleaned = re.sub(r"@[Nn]asz[Kk]ana[l\u0142]", CORRECT_HANDLE, desc)
    # Normalizuj CTA: "Sledz @portalprawypl..." → "▶️ Obserwuj @portalprawypl"
    cleaned = re.sub(
        r"[Śś]led[źz] @portalprawypl[^\n]*",
        f"▶️ Obserwuj {CORRECT_HANDLE}",
        cleaned
    )
    cleaned = re.sub(
        r"[Oo]bserwuj @portalprawypl[^\n!]*",
        f"▶️ Obserwuj {CORRECT_HANDLE}",
        cleaned
    )
    return cleaned


async def main():
    yt = await get_youtube_service()
    results = []

    for vid in ALL_SHORTS:
        try:
            # GET snippet
            resp = yt.videos().list(part="snippet", id=vid).execute()
            items = resp.get("items", [])
            if not items:
                print(f"[NOT FOUND] {vid}")
                results.append({"id": vid, "status": "NOT_FOUND"})
                continue

            snippet = items[0]["snippet"]
            old_desc = snippet.get("description", "")
            new_desc = clean_description(old_desc)

            print(f"PREV: {repr(old_desc[:80])}...")
            print(f"NEW:  {repr(new_desc[:80])}...")

            if old_desc == new_desc:
                print(f"[NO_CHANGE] {vid}")
                results.append({"id": vid, "status": "NO_CHANGE"})
                continue

            # PUT snippet TYLKO (bez status!) — NIE zmieniaj publishAt!
            snippet["description"] = new_desc
            yt.videos().update(
                part="snippet",
                body={"id": vid, "snippet": snippet}
            ).execute()

            print(f"[OK] {vid} — zaktualizowano")
            results.append({"id": vid, "status": "OK"})

        except Exception as e:
            print(f"ERR: {vid} — {e}")
            results.append({"id": vid, "status": "ERROR", "error": str(e)})
            if "quotaExceeded" in str(e):
                print("QUOTA EXCEEDED — stopping")
                break

    print("---FINAL_JSON---")
    success = sum(1 for r in results if r["status"] == "OK")
    no_change = sum(1 for r in results if r["status"] == "NO_CHANGE")
    print(json.dumps({
        "total": len(ALL_SHORTS),
        "processed": len(results),
        "success": success,
        "no_change": no_change,
        "failed": len(results) - success - no_change,
        "results": results
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())