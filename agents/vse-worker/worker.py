#!/usr/bin/env python3
"""
agents/vse-worker/worker.py — Modułowy interfejs wykonawczy vse-worker

Eksportuje standardowy interfejs agentów media-dispatch:
- health_check() -> dict
- process(task: dict) -> dict
- get_status() -> dict
"""

import sys
import json
import argparse
from typing import Dict, Any, Optional

try:
    from .pipeline import VSEPipeline
except ImportError:
    from pipeline import VSEPipeline

_pipeline_instance: Optional[VSEPipeline] = None


def _get_pipeline() -> VSEPipeline:
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = VSEPipeline()
    return _pipeline_instance


def health_check() -> Dict[str, Any]:
    """Weryfikacja dostępności API VSE oraz konfiguracji autoryzacji."""
    return _get_pipeline().health_check()


def process(task: Dict[str, Any]) -> Dict[str, Any]:
    """Przetwarza zadanie wideo przez 4-etapowy pipeline VSE."""
    return _get_pipeline().process(task)


def get_status() -> Dict[str, Any]:
    """Zwraca stan ostatnio przetworzonego zadania lub status pipeline."""
    return _get_pipeline().get_status()


def main():
    parser = argparse.ArgumentParser(description="vse-worker CLI")
    parser.add_argument("--health", action="store_true", help="Uruchom health check")
    parser.add_argument("--status", action="store_true", help="Pobierz aktualny status")
    parser.add_argument("--task", type=str, help="Ścieżka do pliku JSON z taskiem lub inline JSON")
    parser.add_argument("--video-url", type=str, help="Bezpośredni URL filmu YouTube")
    parser.add_argument("--video-id", type=str, help="Identyfikator filmu YouTube")
    parser.add_argument("--local-path", type=str, help="Lokalna ścieżka do pliku wideo dla Shortów")
    parser.add_argument("--portal-id", type=str, help="UUID portalu WordPress")
    parser.add_argument("--channel-id", type=str, help="ID kanału YouTube")
    parser.add_argument("--steps", type=str, help="Kroki do wykonania, np. '1,2,3,4'")

    args = parser.parse_args()

    if args.health:
        res = health_check()
        print(json.dumps(res, indent=2, ensure_ascii=False))
        sys.exit(0 if res.get("status") == "ok" else 1)

    if args.status:
        res = get_status()
        print(json.dumps(res, indent=2, ensure_ascii=False))
        sys.exit(0)

    task = {}
    if args.task:
        task_str = args.task.strip()
        if task_str.startswith("{"):
            task = json.loads(task_str)
        else:
            with open(task_str, "r", encoding="utf-8") as f:
                task = json.load(f)

    if args.video_url:
        task["video_url"] = args.video_url
    if args.video_id:
        task["video_id"] = args.video_id
    if args.local_path:
        task["local_path"] = args.local_path
    if args.portal_id:
        task["portal_id"] = args.portal_id
    if args.channel_id:
        task["channel_id"] = args.channel_id
    if args.steps:
        task["steps"] = [int(s.strip()) for s in args.steps.split(",") if s.strip().isdigit()]

    if not task:
        parser.print_help()
        sys.exit(1)

    res = process(task)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    sys.exit(0 if res.get("status") == "ok" else 1)


if __name__ == "__main__":
    main()
