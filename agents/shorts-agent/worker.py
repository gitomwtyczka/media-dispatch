"""
agents/shorts-agent/worker.py

Autonomiczny worker formatu YouTube Shorts dla architektury media-dispatch.
Integruje VSE Short Machine API (/v1/shorts/describe) z YouTube Data API v3.

Główne funkcje:
    health_check() -> dict       # sprawdza VSE API connectivity + YT token
    process(task: dict) -> dict  # główna funkcja procesująca listę shortów
    get_status() -> dict         # zwraca ostatni stan workera

Zmienne środowiskowe:
    VSE_URL             URL VSE API (domyślnie: http://localhost:8085)
    VSE_API_HOST        Alternatywny host VSE API (np. localhost:8085)
    SHORTS_PORTAL_ID    UUID portalu (domyślnie: 2b047d7d-15a1-4d2f-8463-f89c2275bb73)
    VSE_JWT             Token JWT do VSE API (opcjonalny; fallback: docker/SSH)
    YOUTUBE_OAUTH_TOKEN Token OAuth2 dla YouTube Data API (opcjonalny; fallback: baza VSE)
    SSH_HOST            Host SSH serwera VSE (domyślnie: ubuntu@147.224.162.100)
    SSH_KEY_PATH        Ścieżka do klucza SSH (domyślnie: ~/.ssh/oracle-crimson.key)
"""

import os
import sys
import json
import logging
import datetime
import subprocess
import argparse
from pathlib import Path
from typing import Optional, Dict, Any, List

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [shorts-worker] %(message)s"
)
logger = logging.getLogger("shorts-worker")

DEFAULT_VSE_URL = "http://localhost:8085"
DEFAULT_PORTAL_ID = "2b047d7d-15a1-4d2f-8463-f89c2275bb73"
DEFAULT_CHANNEL_NAME = "@PrawyTV"
DEFAULT_PROVIDER = "claude"

_worker_state: Dict[str, Any] = {
    "status": "idle",
    "last_run_at": None,
    "last_task": None,
    "last_result": None,
    "total_processed": 0,
    "total_success": 0,
    "total_failed": 0
}


def get_vse_url() -> str:
    """Zwraca bazowy URL do VSE API ze zmiennych środowiskowych."""
    url = os.getenv("VSE_URL")
    if not url:
        host = os.getenv("VSE_API_HOST", DEFAULT_VSE_URL)
        if not host.startswith("http://") and not host.startswith("https://"):
            url = f"http://{host}"
        else:
            url = host
    return url.rstrip("/")


def get_portal_id() -> str:
    """Zwraca domyślny lub skonfigurowany w ENV portal UUID."""
    return os.getenv("SHORTS_PORTAL_ID", DEFAULT_PORTAL_ID)


def get_vse_jwt() -> str:
    """
    Pobiera token JWT dla VSE API:
    1. Ze zmiennej VSE_JWT / JWT_TOKEN
    2. Bezpośrednio z kontenera vse-api (jeśli worker działa lokalnie na VPS)
    3. Przez SSH do VPS i docker exec wewnątrz kontenera vse-api
    """
    env_token = os.getenv("VSE_JWT") or os.getenv("JWT_TOKEN")
    if env_token and env_token.strip():
        return env_token.strip()

    token_code = (
        "import os, datetime; "
        "from jose import jwt; "
        "secret = os.environ.get('JWT_SECRET_KEY', ''); "
        "payload = {'sub': '4b97ab0c-98ee-46c6-9be8-d86adc4cb38a', "
        "'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)}; "
        "print(jwt.encode(payload, secret, algorithm='HS256'))"
    )

    # Próba 1: lokalny docker exec
    try:
        cmd = ["docker", "exec", "vse-api", "python3", "-c", token_code]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if r.returncode == 0 and r.stdout.strip():
            candidate = r.stdout.strip().splitlines()[-1].strip()
            if candidate and "." in candidate:
                return candidate
    except Exception:
        pass

    # Próba 2: SSH do serwera VPS
    ssh_host = os.getenv("SSH_HOST", "ubuntu@147.224.162.100")
    ssh_key = os.getenv("SSH_KEY_PATH", os.path.expanduser("~/.ssh/oracle-crimson.key"))
    if not os.path.exists(ssh_key):
        win_key = r"C:\Users\tomas2\.ssh\oracle-crimson.key"
        if os.path.exists(win_key):
            ssh_key = win_key

    try:
        ssh_cmd = [
            "ssh", "-i", ssh_key, "-o", "StrictHostKeyChecking=no", ssh_host,
            f'docker exec vse-api python3 -c "{token_code}"'
        ]
        r = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=30)
        if r.returncode == 0 and r.stdout.strip():
            for line in reversed(r.stdout.strip().splitlines()):
                line = line.strip()
                if len(line) > 20 and "." in line:
                    return line
    except Exception as e:
        logger.warning(f"Błąd pobierania JWT przez SSH: {e}")

    raise RuntimeError("Nie udało się uzyskać tokenu VSE JWT ze zmiennych środowiskowych, Dockera ani SSH.")


def get_youtube_oauth_token(channel_id: Optional[str] = None) -> str:
    """
    Pobiera aktywny OAuth token dla YouTube Data API:
    1. Ze zmiennej YOUTUBE_OAUTH_TOKEN
    2. Z bazy danych VSE (przez _build_credentials w kontenerze vse-api)
    3. Przez SSH do VPS
    """
    env_token = os.getenv("YOUTUBE_OAUTH_TOKEN")
    if env_token and env_token.strip():
        return env_token.strip()

    yt_code = (
        "import asyncio, json; "
        "from api.db import AsyncSessionLocal; "
        "from api.models.youtube_channel import YouTubeChannel; "
        "from api.core.youtube_publish import _build_credentials; "
        "from google.auth.transport.requests import Request; "
        "from sqlalchemy.future import select; "
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
        "                out.append({'id': str(ch.id), 'channel_id': ch.youtube_channel_id, 'title': ch.title, 'error': str(e)})\n"
        "        print(json.dumps(out))\n"
        "asyncio.run(main())"
    )

    raw_output = None
    # Próba 1: lokalny docker exec
    try:
        cmd = ["docker", "exec", "-w", "/app", "vse-api", "python3", "-c", yt_code]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        if r.returncode == 0 and r.stdout.strip():
            raw_output = r.stdout
    except Exception:
        pass

    # Próba 2: SSH do serwera VPS
    if not raw_output:
        ssh_host = os.getenv("SSH_HOST", "ubuntu@147.224.162.100")
        ssh_key = os.getenv("SSH_KEY_PATH", os.path.expanduser("~/.ssh/oracle-crimson.key"))
        if not os.path.exists(ssh_key):
            win_key = r"C:\Users\tomas2\.ssh\oracle-crimson.key"
            if os.path.exists(win_key):
                ssh_key = win_key

        try:
            ssh_cmd = [
                "ssh", "-i", ssh_key, "-o", "StrictHostKeyChecking=no", ssh_host,
                f"docker exec -w /app vse-api python3 -c '{yt_code}'"
            ]
            r = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=35)
            if r.returncode == 0 and r.stdout.strip():
                raw_output = r.stdout
        except Exception as e:
            logger.warning(f"Błąd pobierania YouTube OAuth przez SSH: {e}")

    if raw_output:
        for line in raw_output.strip().splitlines():
            line = line.strip()
            if line.startswith("[") and line.endswith("]"):
                try:
                    channels = json.loads(line)
                    if channel_id:
                        for ch in channels:
                            if ch.get("channel_id") == channel_id and ch.get("token"):
                                return ch["token"]
                    for ch in channels:
                        if ch.get("token"):
                            return ch["token"]
                except Exception as e:
                    logger.warning(f"Błąd parsowania kanałów YouTube JSON: {e}")

    raise RuntimeError("Nie udało się uzyskać tokenu YouTube OAuth z ENV, Dockera ani SSH.")


def describe_short(
    vse_url: str,
    vse_jwt: str,
    source_youtube_id: str,
    start_sec: float,
    end_sec: float,
    portal_id: str,
    channel_name: str = DEFAULT_CHANNEL_NAME,
    provider: str = DEFAULT_PROVIDER
) -> dict:
    """Wywołuje endpoint POST /v1/shorts/describe na instancji VSE."""
    import requests

    url = f"{vse_url}/v1/shorts/describe"
    payload = {
        "youtube_id": source_youtube_id,
        "related_video_id": source_youtube_id,
        "start_sec": float(start_sec),
        "end_sec": float(end_sec),
        "provider": provider,
        "channel_name": channel_name,
        "portal_id": portal_id
    }
    headers = {
        "Authorization": f"Bearer {vse_jwt}",
        "Content-Type": "application/json"
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=120)
    if resp.status_code != 200:
        raise RuntimeError(f"VSE /v1/shorts/describe HTTP {resp.status_code}: {resp.text}")
    return resp.json()


def get_youtube_video(video_id: str, oauth_token: str) -> dict:
    """Pobiera snippet i status filmu z YouTube Data API."""
    import requests

    url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet,status&id={video_id}"
    resp = requests.get(url, headers={"Authorization": f"Bearer {oauth_token}"}, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"YouTube GET {video_id} failed ({resp.status_code}): {resp.text}")
    data = resp.json()
    items = data.get("items", [])
    if not items:
        raise RuntimeError(f"Video {video_id} nie zostało znalezione na YouTube.")
    return items[0]


def update_youtube_metadata(
    video_id: str,
    title: str,
    description: str,
    hashtags: List[str],
    oauth_token: str
) -> dict:
    """Aktualizuje snippet (title, description, tags) na YouTube Data API."""
    import requests

    item = get_youtube_video(video_id, oauth_token)
    snippet = item.get("snippet", {})
    category_id = snippet.get("categoryId", "25")
    existing_tags = snippet.get("tags", [])

    clean_tags = [h.strip() for h in hashtags if h.strip()]
    tags_str = " ".join(clean_tags)
    full_desc = description.strip()
    if tags_str and tags_str not in full_desc:
        full_desc = f"{full_desc}\n\n{tags_str}".strip()

    new_tags = [t.lstrip("#") for t in clean_tags]
    merged_tags = list(dict.fromkeys(existing_tags + new_tags))

    # Tytuł YouTube: max 100 znaków (zalecane front-loaded <= 45 znaków)
    clean_title = title.strip()[:100]

    update_snippet = {
        "title": clean_title,
        "description": full_desc,
        "categoryId": category_id,
        "tags": merged_tags
    }

    put_url = "https://www.googleapis.com/youtube/v3/videos?part=snippet"
    body = {
        "id": video_id,
        "snippet": update_snippet
    }
    resp = requests.put(
        put_url,
        headers={
            "Authorization": f"Bearer {oauth_token}",
            "Content-Type": "application/json"
        },
        json=body,
        timeout=30
    )
    if resp.status_code != 200:
        raise RuntimeError(f"YouTube PUT {video_id} failed ({resp.status_code}): {resp.text}")
    return resp.json()


def insert_pinned_comment(video_id: str, comment_text: str, oauth_token: str) -> dict:
    """Wstawia komentarz z konta kanału przez YouTube commentThreads.insert."""
    import requests

    if not comment_text or not comment_text.strip():
        return {"status": "skipped", "reason": "empty_comment"}

    url = "https://www.googleapis.com/youtube/v3/commentThreads?part=snippet"
    body = {
        "snippet": {
            "videoId": video_id,
            "topLevelComment": {
                "snippet": {
                    "textOriginal": comment_text.strip()
                }
            }
        }
    }
    resp = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {oauth_token}",
            "Content-Type": "application/json"
        },
        json=body,
        timeout=30
    )
    if resp.status_code in (200, 201):
        return {"status": "ok", "comment_id": resp.json().get("id")}
    else:
        return {"status": "error", "code": resp.status_code, "response": resp.text}


def health_check() -> dict:
    """
    Sprawdza VSE API connectivity + YT token.
    Zwraca słownik ze statusem połączeń i szczegółami.
    """
    import requests

    vse_url = get_vse_url()
    vse_ok = False
    vse_details = None
    yt_ok = False
    yt_details = None

    # Test VSE API
    try:
        jwt_token = get_vse_jwt()
        me_resp = requests.get(
            f"{vse_url}/v1/users/me",
            headers={"Authorization": f"Bearer {jwt_token}"},
            timeout=15
        )
        if me_resp.status_code == 200:
            vse_ok = True
            vse_details = me_resp.json()
        else:
            vse_details = f"HTTP {me_resp.status_code}: {me_resp.text}"
    except Exception as e:
        vse_details = str(e)

    # Test YouTube OAuth token
    try:
        yt_token = get_youtube_oauth_token()
        yt_test = requests.get(
            "https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true",
            headers={"Authorization": f"Bearer {yt_token}"},
            timeout=15
        )
        if yt_test.status_code == 200:
            yt_ok = True
            items = yt_test.json().get("items", [])
            channel_title = items[0]["snippet"]["title"] if items else "Unknown"
            yt_details = {"channel_title": channel_title}
        else:
            yt_details = f"HTTP {yt_test.status_code}: {yt_test.text}"
    except Exception as e:
        yt_details = str(e)

    overall_status = "ok" if (vse_ok and yt_ok) else ("degraded" if (vse_ok or yt_ok) else "error")

    return {
        "status": overall_status,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "vse_api": {
            "url": vse_url,
            "connected": vse_ok,
            "details": vse_details
        },
        "youtube": {
            "token_valid": yt_ok,
            "details": yt_details
        }
    }


def process(task: dict) -> dict:
    """
    Główna funkcja procesująca listę shortów.

    task:
    {
        "shorts": [
            {
                "short_id": "...",
                "source_youtube_id": "...",
                "start_sec": 0.0,
                "end_sec": 60.0,
                "name": "..."  # opcjonalnie
            }
        ],
        "portal_id": "...",             # opcjonalnie, default z env
        "channel_name": "@PrawyTV",     # opcjonalnie
        "provider": "claude",           # opcjonalnie
        "insert_pinned_comment": False  # opcjonalnie
    }
    """
    shorts_list = task.get("shorts", [])
    if not shorts_list:
        return {
            "status": "error",
            "error": "Brak listy shortów w task['shorts']",
            "total": 0,
            "success": 0,
            "failed": 0,
            "results": []
        }

    portal_id = task.get("portal_id") or get_portal_id()
    channel_name = task.get("channel_name", DEFAULT_CHANNEL_NAME)
    provider = task.get("provider", DEFAULT_PROVIDER)
    should_insert_comment = task.get("insert_pinned_comment", False)

    vse_url = get_vse_url()
    vse_jwt = get_vse_jwt()
    yt_token = get_youtube_oauth_token()

    results = []
    success_count = 0
    fail_count = 0

    logger.info(f"Rozpoczynam przetwarzanie {len(shorts_list)} shortów...")

    for item in shorts_list:
        short_id = item.get("short_id")
        source_id = item.get("source_youtube_id") or short_id
        start_s = float(item.get("start_sec", 0.0))
        end_s = float(item.get("end_sec", 60.0))
        name = item.get("name", short_id)

        item_res: Dict[str, Any] = {
            "short_id": short_id,
            "source_youtube_id": source_id,
            "name": name,
            "start_sec": start_s,
            "end_sec": end_s,
            "describe_status": "PENDING",
            "yt_update_status": "PENDING",
            "error": None
        }

        # 1. Opis z Short Machine
        try:
            logger.info(f"Opisywanie shorta {short_id} (źródło {source_id}, {start_s}s-{end_s}s)...")
            desc_res = describe_short(
                vse_url=vse_url,
                vse_jwt=vse_jwt,
                source_youtube_id=source_id,
                start_sec=start_s,
                end_sec=end_s,
                portal_id=portal_id,
                channel_name=channel_name,
                provider=provider
            )
            item_res["describe_status"] = "OK"
            item_res["describe_result"] = desc_res
        except Exception as e:
            logger.error(f"Błąd describe dla {short_id}: {e}")
            item_res["describe_status"] = "ERROR"
            item_res["error"] = str(e)
            fail_count += 1
            results.append(item_res)
            continue

        opt_title = desc_res.get("optimized_title") or desc_res.get("suggested_title") or desc_res.get("title") or ""
        desc_text = desc_res.get("description", "")
        hashtags = desc_res.get("hashtags", [])
        pinned_comment = desc_res.get("pinned_comment")

        # 2. Aktualizacja YouTube snippet
        try:
            logger.info(f"Aktualizacja metadanych na YouTube dla {short_id}...")
            update_youtube_metadata(
                video_id=short_id,
                title=opt_title,
                description=desc_text,
                hashtags=hashtags,
                oauth_token=yt_token
            )
            item_res["yt_update_status"] = "OK"
            item_res["updated_title"] = opt_title
            success_count += 1
        except Exception as e:
            logger.error(f"Błąd aktualizacji YouTube dla {short_id}: {e}")
            item_res["yt_update_status"] = "ERROR"
            item_res["error"] = str(e)
            fail_count += 1

        # 3. Opcjonalny przypięty komentarz
        if should_insert_comment and pinned_comment:
            try:
                c_res = insert_pinned_comment(short_id, pinned_comment, yt_token)
                item_res["pinned_comment_status"] = c_res.get("status")
            except Exception as e:
                item_res["pinned_comment_status"] = f"ERROR: {e}"

        results.append(item_res)

    _worker_state["status"] = "idle"
    _worker_state["last_run_at"] = datetime.datetime.utcnow().isoformat() + "Z"
    _worker_state["last_task"] = task
    _worker_state["last_result"] = results
    _worker_state["total_processed"] += len(shorts_list)
    _worker_state["total_success"] += success_count
    _worker_state["total_failed"] += fail_count

    overall_status = "ok" if fail_count == 0 else ("partial" if success_count > 0 else "error")

    summary = {
        "status": overall_status,
        "total": len(shorts_list),
        "success": success_count,
        "failed": fail_count,
        "results": results
    }
    logger.info(f"Zakończono: status={overall_status} (sukces: {success_count}/{len(shorts_list)})")
    return summary


def get_status() -> dict:
    """Zwraca ostatni stan workera."""
    st = dict(_worker_state)
    st["current_time"] = datetime.datetime.utcnow().isoformat() + "Z"
    return st


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Shorts Agent Worker")
    parser.add_argument("--health", action="store_true", help="Wykonaj test połączenia z VSE API i YouTube")
    parser.add_argument("--status", action="store_true", help="Pobierz aktualny stan workera")
    parser.add_argument("--task-file", help="Ścieżka do pliku JSON ze specyfikacją zadania (task)")
    parser.add_argument("--task-json", help="String JSON ze specyfikacją zadania (task)")

    args = parser.parse_args()

    if args.health:
        print(json.dumps(health_check(), indent=2, ensure_ascii=False))
    elif args.status:
        print(json.dumps(get_status(), indent=2, ensure_ascii=False))
    elif args.task_file:
        with open(args.task_file, "r", encoding="utf-8") as f:
            t = json.load(f)
        print(json.dumps(process(t), indent=2, ensure_ascii=False))
    elif args.task_json:
        t = json.loads(args.task_json)
        print(json.dumps(process(t), indent=2, ensure_ascii=False))
    else:
        parser.print_help()
