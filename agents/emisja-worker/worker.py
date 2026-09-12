"""agents/emisja-worker/worker.py

Standardowy interfejs workera media-dispatch dla modułu emisja-worker.
Udostępnia funkcje:
- health_check() -> dict
- process(task: dict) -> dict
- get_status() -> dict
Oraz CLI do uruchamiania ręcznego i przez cron/skrypty orkiestracji.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Any, Dict, Optional

try:
    from .collab_linker import CollabLinker
except ImportError:
    from collab_linker import CollabLinker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("emisja-worker")

_default_linker: Optional[CollabLinker] = None


def get_linker(config: Optional[Dict[str, Any]] = None) -> CollabLinker:
    """Zwraca instancję CollabLinker (singleton jeśli brak specyficznej konfiguracji)."""
    global _default_linker
    if config:
        return CollabLinker(config)
    if _default_linker is None:
        _default_linker = CollabLinker()
    return _default_linker


def health_check() -> Dict[str, Any]:
    """Weryfikuje konfigurację i połączenia do Google Sheets oraz WordPress API.

    Returns:
        Dict[str, Any]: Słownik stanu komponentów.
    """
    return get_linker().health_check()


def process(task: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Generuje linki draft-collab i aktualizuje arkusz Emisja.

    Args:
        task: Słownik konfiguracji zadania.

    Returns:
        Dict[str, Any]: Raport z wykonania.
    """
    return get_linker().process(task)


def get_status() -> Dict[str, Any]:
    """Zwraca ostatni stan i status konfiguracji workera."""
    return get_linker().get_status()


def main():
    """Punkt wejścia CLI."""
    parser = argparse.ArgumentParser(
        description="emisja-worker / CollabLinker — automatyczne generowanie linków draft-collab do WordPress z arkusza Emisja"
    )
    parser.add_argument(
        "--health",
        action="store_true",
        help="Uruchom health check i wyświetl status komponentów",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Wyświetl ostatni stan wykonania workera",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Tryb symulacji: generuj linki, ale nie zapisuj ich do arkusza Sheets",
    )
    parser.add_argument(
        "--sheet-id",
        type=str,
        default=None,
        help="ID arkusza Google Sheets (nadpisuje SHEETS_EMISJA_ID)",
    )
    parser.add_argument(
        "--sheet-name",
        type=str,
        default="Emisja",
        help="Nazwa zakładki w arkuszu (domyślnie 'Emisja')",
    )
    parser.add_argument(
        "--wp-url-col",
        type=str,
        default="WP Draft URL",
        help="Nazwa kolumny zawierającej linki do draftów WP (domyślnie 'WP Draft URL')",
    )
    parser.add_argument(
        "--collab-col",
        type=str,
        default="Link draft",
        help="Nazwa kolumny docelowej dla linków collab (domyślnie 'Link draft')",
    )
    parser.add_argument(
        "--email",
        type=str,
        default=None,
        help="Email współpracownika do autoryzacji linku (nadpisuje COLLAB_EMAIL)",
    )
    parser.add_argument(
        "--expire-on-publish",
        action="store_true",
        help="Oznacz link jako wygasający natychmiast po publikacji artykułu",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Wymuś wygenerowanie linku nawet jeśli wiersz już posiada link collab",
    )

    args = parser.parse_args()

    if args.health:
        res = health_check()
        print(json.dumps(res, indent=2, ensure_ascii=False))
        sys.exit(0 if res.get("healthy") else 1)

    if args.status:
        res = get_status()
        print(json.dumps(res, indent=2, ensure_ascii=False))
        sys.exit(0)

    task: Dict[str, Any] = {
        "sheet_name": args.sheet_name,
        "wp_url_column": args.wp_url_col,
        "collab_column": args.collab_col,
        "expire_on_publish": args.expire_on_publish,
        "dry_run": args.dry_run,
        "force_refresh": args.force,
    }

    if args.sheet_id:
        task["sheet_id"] = args.sheet_id
    if args.email:
        task["collab_email"] = args.email

    res = process(task)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    sys.exit(0 if res.get("status") in ("ok", "partial") else 1)


if __name__ == "__main__":
    main()
