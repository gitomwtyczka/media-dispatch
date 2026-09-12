"""
agents/shorts-agent/scheduler.py

Scheduler dla zatwierdzonych shortów w architekturze media-dispatch.
Ustawia privacyStatus='private' oraz publishAt na YouTube Data API v3.

Główne funkcje:
    schedule_short(short_id: str, publish_at_utc: str, title: str, description: str) -> dict
    schedule_shorts_batch(shorts: list, oauth_token: Optional[str] = None) -> list

Zmienne środowiskowe:
    YOUTUBE_OAUTH_TOKEN Token OAuth2 dla YouTube Data API (opcjonalny; fallback: worker / baza VSE)
    SSH_HOST            Host SSH serwera VSE (domyślnie: ubuntu@147.224.162.100)
    SSH_KEY_PATH        Ścieżka do klucza SSH (domyślnie: ~/.ssh/oracle-crimson.key)
"""

import os
import sys
import json
import logging
import argparse
from typing import Optional, Dict, Any, List
from pathlib import Path

# Próba importu pomocników tokenów i API z workera
try:
    from agents.shorts_agent.worker import get_youtube_oauth_token, get_youtube_video
except ImportError:
    try:
        from worker import get_youtube_oauth_token, get_youtube_video
    except ImportError:
        def get_youtube_oauth_token(channel_id: Optional[str] = None) -> str:
            token = os.getenv("YOUTUBE_OAUTH_TOKEN")
            if token and token.strip():
                return token.strip()
            raise RuntimeError("Brak YOUTUBE_OAUTH_TOKEN w środowisku oraz nie można zaimportować z worker.py.")

        def get_youtube_video(video_id: str, oauth_token: str) -> dict:
            import requests
            url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet,status&id={video_id}"
            resp = requests.get(url, headers={"Authorization": f"Bearer {oauth_token}"}, timeout=30)
            if resp.status_code != 200:
                raise RuntimeError(f"YouTube GET {video_id} failed ({resp.status_code}): {resp.text}")
            items = resp.json().get("items", [])
            if not items:
                raise RuntimeError(f"Video {video_id} nie zostało znalezione na YouTube.")
            return items[0]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [shorts-scheduler] %(message)s"
)
logger = logging.getLogger("shorts-scheduler")


def schedule_short(
    short_id: str,
    publish_at_utc: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    oauth_token: Optional[str] = None
) -> dict:
    """
    Planuje publikację shorta na YouTube.
    Ustawia privacyStatus='private' oraz publishAt (wymóg YouTube Data API: publishAt działa wyłącznie gdy privacyStatus jest private).
    Jeżeli title lub description są podane, aktualizuje również snippet wideo.

    Args:
        short_id: Identyfikator YouTube shorta.
        publish_at_utc: Data i godzina publikacji w formacie ISO UTC (np. '2026-09-15T07:00:00Z').
                        Jeśli None, wideo ustawiane jest w trybie 'private' bez harmonogramu.
        title: Opcjonalny zoptymalizowany tytuł do zapisania.
        description: Opcjonalny zoptymalizowany opis do zapisania.
        oauth_token: Token autoryzacyjny OAuth2 (jeśli brak, pobierany automatycznie).

    Returns:
        Słownik ze statusem operacji.
    """
    import requests

    token = oauth_token or get_youtube_oauth_token()
    logger.info(f"Planowanie shorta {short_id} (publishAt={publish_at_utc})...")

    # 1. Pobierz aktualne metadane filmu z YouTube
    try:
        item = get_youtube_video(short_id, token)
    except Exception as e:
        logger.error(f"Nie można pobrać wideo {short_id}: {e}")
        return {
            "short_id": short_id,
            "success": False,
            "error": f"Pobieranie wideo z YouTube nie powiodło się: {e}"
        }

    snippet = item.get("snippet", {})
    if title:
        snippet["title"] = title.strip()[:100]
    if description:
        snippet["description"] = description.strip()

    # 2. Przygotuj status prywatny + publishAt
    new_status: Dict[str, Any] = {"privacyStatus": "private"}
    if publish_at_utc:
        new_status["publishAt"] = publish_at_utc.strip()

    update_body = {
        "id": short_id,
        "snippet": snippet,
        "status": new_status
    }

    put_url = "https://www.googleapis.com/youtube/v3/videos?part=snippet,status"
    put_resp = requests.put(
        put_url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json=update_body,
        timeout=30
    )

    if put_resp.status_code == 200:
        logger.info(f"Short {short_id} zaplanowany pomyślnie na {publish_at_utc}")
        return {
            "short_id": short_id,
            "success": True,
            "status": "scheduled" if publish_at_utc else "private",
            "publish_at": publish_at_utc,
            "title": snippet.get("title"),
            "error": None
        }

    # 3. Fallback: jeśli wystąpił błąd przy zapisie z publishAt, spróbuj zapisać sam status 'private'
    logger.warning(
        f"Błąd przy zapisie z publishAt dla {short_id} (HTTP {put_resp.status_code}): {put_resp.text}. Próba fallback bez publishAt..."
    )
    fallback_body = {
        "id": short_id,
        "snippet": snippet,
        "status": {"privacyStatus": "private"}
    }
    fb_resp = requests.put(
        put_url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json=fallback_body,
        timeout=30
    )

    if fb_resp.status_code == 200:
        logger.info(f"Short {short_id} zapisany w trybie private (fallback udany)")
        return {
            "short_id": short_id,
            "success": False,
            "fallback_success": True,
            "status": "private_fallback_no_publish_at",
            "publish_at_requested": publish_at_utc,
            "title": snippet.get("title"),
            "error": f"HTTP {put_resp.status_code} przy publishAt: {put_resp.text}. Ustawiono private pomyślnie."
        }
    else:
        logger.error(f"Fallback również nie powiódł się dla {short_id}: HTTP {fb_resp.status_code}")
        return {
            "short_id": short_id,
            "success": False,
            "fallback_success": False,
            "status": "failed",
            "publish_at_requested": publish_at_utc,
            "error": f"PUT failed: {put_resp.text} | Fallback failed: {fb_resp.text}"
        }


def schedule_shorts_batch(
    shorts: List[Dict[str, Any]],
    oauth_token: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Planuje listę shortów w pętli.

    shorts: lista obiektów, np.
    [
        {
            "id": "abc123short",
            "publishAt": "2026-09-15T07:00:00Z",
            "title": "Tytuł",
            "description": "Opis"
        }
    ]
    """
    token = oauth_token or get_youtube_oauth_token()
    results = []
    for item in shorts:
        vid = item.get("id") or item.get("short_id")
        if not vid:
            continue
        pub_at = item.get("publishAt") or item.get("publish_at")
        title = item.get("title")
        desc = item.get("description")
        res = schedule_short(
            short_id=vid,
            publish_at_utc=pub_at,
            title=title,
            description=desc,
            oauth_token=token
        )
        results.append(res)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Shorts YouTube Scheduler")
    parser.add_argument("--video-id", help="Identyfikator shorta YouTube")
    parser.add_argument("--publish-at", help="Data publikacji ISO UTC (np. 2026-09-15T07:00:00Z)")
    parser.add_argument("--title", help="Zaktualizowany tytuł shorta")
    parser.add_argument("--description", help="Zaktualizowany opis shorta")
    parser.add_argument("--batch-file", help="Plik JSON z listą shortów do zaplanowania")

    args = parser.parse_args()

    if args.video_id:
        res = schedule_short(
            short_id=args.video_id,
            publish_at_utc=args.publish_at,
            title=args.title,
            description=args.description
        )
        print(json.dumps(res, indent=2, ensure_ascii=False))
    elif args.batch_file:
        with open(args.batch_file, "r", encoding="utf-8") as f:
            batch_data = json.load(f)
        res = schedule_shorts_batch(batch_data)
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        parser.print_help()
