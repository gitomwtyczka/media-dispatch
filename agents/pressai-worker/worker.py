#!/usr/bin/env python3
"""agents/pressai-worker/worker.py

Wrapper roboczy dla AutoPublisher w ramach ekosystemu media-dispatch.
media-dispatch | media-dev-B | 12.09.2026

Eksportuje standardowy interfejs workera:
  - health_check() -> dict
  - process(task: dict) -> dict
  - get_status() -> dict

Użycie jako moduł:
  from agents.pressai_worker.worker import health_check, process, get_status

CLI:
  python worker.py --health
  python worker.py --status
  python worker.py --auto-pick
  python worker.py --url https://...
  python worker.py --process '{"source_url": "https://...", "target_portal": "Kurier365"}'
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Obsługa importu relatywnego i bezwzględnego
try:
    from .auto_publisher import AutoPublisher
except ImportError:
    current_dir = Path(__file__).parent.resolve()
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))
    project_root = current_dir.parent.parent.resolve()
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from auto_publisher import AutoPublisher

logger = logging.getLogger("pressai-worker")

_default_publisher: Optional[AutoPublisher] = None


def get_publisher(config: Optional[Dict[str, Any]] = None) -> AutoPublisher:
    """Zwraca instancję singletona AutoPublisher."""
    global _default_publisher
    if _default_publisher is None or config is not None:
        _default_publisher = AutoPublisher(config=config)
    return _default_publisher


def health_check() -> Dict[str, Any]:
    """Sprawdza połączenie z PressAI oraz Feed Crawler."""
    return get_publisher().health_check()


def process(task: Dict[str, Any]) -> Dict[str, Any]:
    """Przetwarza zadanie publikacji artykułu.

    Przyjmuje:
      task = {
          "source_url": "...",
          "source_text": "...",
          "auto_pick": True/False,
          "portal": "Kurier365",
          "target_portal": "Kurier365",
          "portal_id": 1,
          "model_provider": "anthropic",
          "model_name": "claude-sonnet-4-5",
          "custom_instructions": "..."
      }
    Zwraca:
      {
          "status": "ok" / "error",
          "article_id": "...",
          "wp_post_id": ...,
          "wp_edit_url": "...",
          "source_url": "..."
      }
    """
    return get_publisher().process(task)


def get_status() -> Dict[str, Any]:
    """Zwraca ostatni status wykonania workera."""
    return get_publisher().get_status()


def main():
    parser = argparse.ArgumentParser(
        description="pressai-worker — autonomiczny worker publikacji dla WordPress przez PressAI"
    )
    parser.add_argument("--health", action="store_true", help="Sprawdź stan połączeń")
    parser.add_argument("--status", action="store_true", help="Pokaż status workera")
    parser.add_argument("--auto-pick", action="store_true", help="Pobierz i opublikuj z feed-crawlera")
    parser.add_argument("--url", type=str, help="URL źródłowy artykułu")
    parser.add_argument("--text", type=str, help="Treść źródłowa artykułu")
    parser.add_argument("--portal", type=str, default="Kurier365", help="Docelowy portal (domyślnie: Kurier365)")
    parser.add_argument("--portal-id", type=int, help="ID portalu WordPress")
    parser.add_argument("--process", dest="process_json", type=str, help="Zadanie w JSON do przetworzenia")
    parser.add_argument("--json", action="store_true", help="Formatuj output jako JSON")

    args = parser.parse_args()

    if args.health:
        res = health_check()
        print(json.dumps(res, indent=2, ensure_ascii=False) if args.json else f"Health: {res['status']} (PressAI: {res['pressai_connected']}, FeedCrawler: {res['feed_crawler_connected']})")
        sys.exit(0 if res["status"] in ("ok", "degraded") else 1)

    if args.status:
        res = get_status()
        print(json.dumps(res, indent=2, ensure_ascii=False))
        sys.exit(0)

    task: Dict[str, Any] = {}
    if args.process_json:
        try:
            task = json.loads(args.process_json)
        except json.JSONDecodeError as e:
            print(f"Błąd parsowania JSON: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        if args.auto_pick:
            task["auto_pick"] = True
        if args.url:
            task["source_url"] = args.url
        if args.text:
            task["source_text"] = args.text
        if args.portal:
            task["target_portal"] = args.portal
        if args.portal_id:
            task["portal_id"] = args.portal_id

    if not task:
        parser.print_help()
        sys.exit(0)

    res = process(task)
    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        print(f"Status: {res.get('status')}")
        if res.get("status") == "ok":
            print(f"Article ID: {res.get('article_id')}")
            print(f"WP Post ID: {res.get('wp_post_id')}")
            print(f"WP Edit URL: {res.get('wp_edit_url')}")
        else:
            print(f"Error: {res.get('error')}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
