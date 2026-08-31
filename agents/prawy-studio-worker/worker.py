#!/usr/bin/env python3
"""
prawy-studio-worker — Dedykowany worker dla Studio Prawy_PL
media-dispatch | media-dev-04 | 31.08.2026

Pipeline: generate_token -> check_captions -> generate SEO -> inject WP -> yt_update -> shorts

CLI:
  python worker.py --single YOUTUBE_ID [--date 2026-09-01] [--status draft|future|publish]
  python worker.py --batch films.json
  python worker.py --list
  python worker.py --shorts-only YOUTUBE_ID
  python worker.py --check-captions YOUTUBE_ID
  python worker.py --reset YOUTUBE_ID
"""

import argparse
import json
import logging
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# KONFIGURACJA — dostosuj do srodowiska
# ---------------------------------------------------------------------------

VSE_URL = "https://vse.impresjapr.pl"
PORTAL_ID = "2b047d7d-15a1-4d2f-8463-f89c2275bb73"   # UUID prawy.pl
YT_CHANNEL_ID = "UCoH2G9By4OX3kcLsc8lHgDw"            # Studio Prawy_PL
SSH_HOST = "ubuntu@147.224.162.100"
SSH_KEY = r"C:\Users\tomas2\.ssh\oracle-crimson.key"
DOCKER_CONTAINER = "vse-api"
USER_ID = "4b97ab0c-98ee-46c6-9be8-d86adc4cb38a"       # tobroz@gmail.com
LOCAL_VIDEO_DIR = r"C:\Users\tomas2\Videos\Prawy"
OUTPUT_DIR = r"C:\VSE\Shorts"
STATE_FILE = Path(__file__).parent / "batch_progress.json"

# Pipeline defaults
LLM_PROVIDER = "claude"          # VPS ma tylko ANTHROPIC_API_KEY!
PUBLICATION_TYPE = "full_analysis"  # NIE 'film'!
LANG = "pl"
DEFAULT_POST_STATUS = "future"

# Retry
MAX_RETRIES = 3
RETRY_DELAY = 10  # sekund

# Captions polling
CAPTIONS_POLL_INTERVAL = 30  # sekund
CAPTIONS_MAX_WAIT = 10 * 60  # 10 minut

# Timeouts
T_GENERATE = 300
T_INJECT = 120
T_CANDIDATES = 180
T_RENDER = 30
T_SSH = 30

# ---------------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------------

log_path = Path(__file__).parent / "worker.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_path, encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# STATE / CHECKPOINT
# ---------------------------------------------------------------------------

def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

# ---------------------------------------------------------------------------
# AUTH
# ---------------------------------------------------------------------------

def generate_token() -> str:
    """Generuje JWT token przez docker exec w kontenerze vse-api.

    Uzywa jose.jwt.encode() z JWT_SECRET_KEY — jedyna niezawodna metoda.
    Patrz VSE Constitution sekcja 2.
    """
    log.info("Generowanie JWT token przez docker exec...")
    code = (
        "import os, datetime; "
        "from jose import jwt; "
        "s = os.environ.get('JWT_SECRET_KEY', ''); "
        f"p = {{'sub': '{USER_ID}', "
        "'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)}}; "
        "print(jwt.encode(p, s, algorithm='HS256'))"
    )
    cmd = [
        "ssh", "-i", SSH_KEY,
        "-o", "StrictHostKeyChecking=no",
        SSH_HOST,
        f"docker exec {DOCKER_CONTAINER} python3 -c {json.dumps(code)}",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=T_SSH)
    token = r.stdout.strip()
    if not token or r.returncode != 0:
        raise RuntimeError(f"generate_token FAIL: {r.stderr.strip()}")
    log.info("Token wygenerowany OK (dlugosc: %d)", len(token))
    return token


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# ---------------------------------------------------------------------------
# RETRY HELPER
# ---------------------------------------------------------------------------

def with_retry(fn, step_name: str, max_retries: int = MAX_RETRIES, delay: int = RETRY_DELAY):
    """Uruchamia fn() z retry logic. Rzuca wyjatek po wyczerpaniu prob."""
    for attempt in range(1, max_retries + 1):
        try:
            return fn()
        except Exception as e:
            if attempt < max_retries:
                log.warning("%s: proba %d/%d nieudana: %s — czekam %ds",
                            step_name, attempt, max_retries, e, delay)
                time.sleep(delay)
            else:
                log.error("%s: wszystkie %d proby nieudane. Ostatni blad: %s",
                          step_name, max_retries, e)
                raise

# ---------------------------------------------------------------------------
# CAPTIONS CHECK
# ---------------------------------------------------------------------------

def check_captions_ready(youtube_id: str, headers: dict, wait: bool = True) -> bool:
    """Sprawdza czy napisy YT sa gotowe.

    Probuje wywolac /v1/generate w trybie 'check' (kroki 1 z timeout 10s).
    Jezeli VSE zwroci blad zwiazany z napisami — czeka i ponawia.
    Zwraca True gdy gotowe, False gdy timeout.
    """
    url = f"https://www.youtube.com/watch?v={youtube_id}"
    log.info("[captions] Sprawdzam gotowose napisow dla %s...", youtube_id)

    deadline = time.time() + CAPTIONS_MAX_WAIT
    attempt = 0
    while True:
        attempt += 1
        try:
            resp = requests.post(
                f"{VSE_URL}/v1/generate",
                headers=headers,
                json={
                    "video_url": url,
                    "llm_provider": LLM_PROVIDER,
                    "lang": LANG,
                    "publication_type": PUBLICATION_TYPE,
                    "portal_id": PORTAL_ID,
                    "check_captions_only": True,  # VSE ignoruje nieznane pola — wrocic z pelnym generate
                },
                timeout=20,
            )
            if resp.status_code == 200:
                log.info("[captions] Napisy gotowe (proba %d).", attempt)
                return True
            body = resp.text[:200]
            log.warning("[captions] HTTP %d: %s", resp.status_code, body)
        except requests.RequestException as e:
            log.warning("[captions] Blad polaczenia proba %d: %s", attempt, e)

        if not wait or time.time() > deadline:
            log.warning("[captions] Timeout (%ds) — napisy niedostepne dla %s",
                        CAPTIONS_MAX_WAIT, youtube_id)
            return False

        remaining = int(deadline - time.time())
        log.info("[captions] Czekam %ds (pozostalo ~%ds do timeout)...",
                 CAPTIONS_POLL_INTERVAL, remaining)
        time.sleep(CAPTIONS_POLL_INTERVAL)

# ---------------------------------------------------------------------------
# PIPELINE STEPS
# ---------------------------------------------------------------------------

def run_generate(youtube_id: str, portal_id: str, headers: dict) -> dict:
    """Krok 1: Generuj SEO metadata z YouTube URL.
    Zwraca schema_data.
    """
    log.info("  [1/5] Generowanie SEO dla %s...", youtube_id)

    def _call():
        resp = requests.post(
            f"{VSE_URL}/v1/generate",
            headers=headers,
            json={
                "video_url": f"https://www.youtube.com/watch?v={youtube_id}",
                "llm_provider": LLM_PROVIDER,
                "lang": LANG,
                "publication_type": PUBLICATION_TYPE,  # NIE 'film'!
                "portal_id": portal_id,                # UUID, NIE string!
            },
            timeout=T_GENERATE,
        )
        resp.raise_for_status()
        data = resp.json()
        schema = data.get("schema_data") or data
        if not schema:
            raise ValueError("Pusty schema_data w odpowiedzi")
        return schema

    result = with_retry(_call, "run_generate")
    log.info("  [1/5] SEO OK — post_title: %s", result.get("post_title", "")[:60])
    return result


def run_inject(
    youtube_id: str,
    schema_data: dict,
    portal_id: str,
    headers: dict,
    post_status: str = DEFAULT_POST_STATUS,
    scheduled_date: str | None = None,
) -> tuple[str | None, str | None]:
    """Krok 2: Wstrzyknij artykul do WordPress.
    Zwraca (wp_post_id, wp_url).
    """
    log.info("  [2/5] Inject do prawy.pl (status=%s, date=%s)...", post_status, scheduled_date)

    payload = {
        "video_url": f"https://www.youtube.com/watch?v={youtube_id}",
        "schema_data": schema_data,
        "portal_id": portal_id,
        "yt_channel_ids": [YT_CHANNEL_ID],
        "post_status": post_status,
        "post_format": "video",
    }
    if scheduled_date and post_status == "future":
        # ISO 8601 z godziną 00:00 CEST (+02:00)
        payload["scheduled_date"] = f"{scheduled_date}T00:00:00+02:00"

    def _call():
        resp = requests.post(
            f"{VSE_URL}/v1/inject",
            headers=headers,
            json=payload,
            timeout=T_INJECT,
        )
        resp.raise_for_status()
        return resp.json()

    result = with_retry(_call, "run_inject")
    wp_post_id = result.get("wp_post_id")
    wp_url = result.get("post_url")
    log.info("  [2/5] Inject OK — WP post_id=%s url=%s", wp_post_id, wp_url)
    return wp_post_id, wp_url


def run_yt_update(
    youtube_id: str,
    channel_id: str,
    schema_data: dict,
    headers: dict,
    scheduled_date: str | None = None,
) -> bool:
    """Krok 3: Zaktualizuj opis i metadane na YouTube.
    Zwraca True jesli sukces.
    """
    log.info("  [3/5] YouTube update dla %s...", youtube_id)

    payload = {
        "youtube_id": youtube_id,
        "channel_id": channel_id,
        "schema_data": schema_data,
    }
    if scheduled_date:
        payload["scheduled_date"] = f"{scheduled_date}T00:00:00+02:00"

    def _call():
        resp = requests.post(
            f"{VSE_URL}/v1/youtube/publish-description",
            headers=headers,
            json=payload,
            timeout=T_GENERATE,
        )
        if resp.status_code == 401:
            raise RuntimeError("YT OAuth invalid_grant lub token wygasl — zglос do Supervisora!")
        resp.raise_for_status()
        return resp.json()

    try:
        with_retry(_call, "run_yt_update")
        log.info("  [3/5] YT update OK")
        return True
    except Exception as e:
        # YT update jest opcjonalny — nie blokujemy pipeline
        log.warning("  [3/5] YT update FAIL (nieblokujacy): %s", e)
        return False


def run_shorts_candidates(youtube_id: str, portal_id: str, headers: dict) -> list:
    """Krok 4: Generuj propozycje shortow.
    Zwraca liste kandydatow.
    """
    log.info("  [4/5] Short candidates dla %s...", youtube_id)

    def _call():
        resp = requests.post(
            f"{VSE_URL}/v1/shorts/candidates",
            headers=headers,
            json={
                "youtube_url": f"https://www.youtube.com/watch?v={youtube_id}",
                "youtube_id": youtube_id,
                "count_emotional": 5,
                "count_professional": 5,
                "provider": LLM_PROVIDER,
                "portal_id": portal_id,
            },
            timeout=T_CANDIDATES,
        )
        resp.raise_for_status()
        return resp.json().get("candidates", [])

    candidates = with_retry(_call, "run_shorts_candidates")
    log.info("  [4/5] Candidates OK — %d propozycji", len(candidates))
    return candidates


def run_shorts_render(
    youtube_id: str,
    candidates: list,
    portal_id: str,
    headers: dict,
    local_path: str | None = None,
) -> list:
    """Krok 5: Renderuj top-10 shortow.
    Zwraca liste job_ids.
    """
    top = sorted(candidates, key=lambda c: c.get("score", 0), reverse=True)[:10]
    log.info("  [5/5] Renderowanie %d shortow dla %s...", len(top), youtube_id)
    job_ids = []
    for c in top:
        payload = {
            "youtube_url": f"https://www.youtube.com/watch?v={youtube_id}",
            "youtube_id": youtube_id,
            "start_sec": c["start_sec"],
            "end_sec": c["end_sec"],
            "candidate_data": c,
            "render_format": "9:16",
            "subtitles": "none",
            "output_dir": OUTPUT_DIR,
            "portal_id": portal_id,
        }
        if local_path:
            payload["local_path"] = local_path

        def _call(p=payload):
            resp = requests.post(
                f"{VSE_URL}/v1/shorts/render",
                headers=headers,
                json=p,
                timeout=T_RENDER,
            )
            resp.raise_for_status()
            return resp.json().get("job_id")

        try:
            job_id = with_retry(_call, "run_shorts_render")
            if job_id:
                job_ids.append(job_id)
        except Exception as e:
            log.warning("  Render dla kandydata [%s-%s] FAIL: %s",
                        c.get("start_sec"), c.get("end_sec"), e)
        time.sleep(1)

    log.info("  [5/5] Render zlecony: %d job_ids", len(job_ids))
    return job_ids


def find_local_file(film: dict) -> str | None:
    """Szuka lokalnego pliku wideo dla danego filmu."""
    if film.get("local_path") and Path(film["local_path"]).exists():
        return film["local_path"]
    video_dir = Path(LOCAL_VIDEO_DIR)
    if not video_dir.exists():
        return None
    youtube_id = film["youtube_id"]
    for f in video_dir.glob(f"*{youtube_id}*"):
        if f.suffix.lower() in (".mp4", ".mov", ".mkv"):
            return str(f)
    return None

# ---------------------------------------------------------------------------
# FULL PIPELINE
# ---------------------------------------------------------------------------

def process_film(
    film: dict,
    state: dict,
    headers: dict,
    post_status: str = DEFAULT_POST_STATUS,
    scheduled_date: str | None = None,
) -> bool:
    """Pelny pipeline dla jednego filmu z checkpointowaniem.

    Kazdy krok zapisuje stan — rerun kontynuuje od miejsca bledu.
    """
    youtube_id = film["youtube_id"]
    title = film.get("title", youtube_id)
    # Per-film date/status nadpisuje globalne jesli podane w JSON
    f_status = film.get("post_status", post_status)
    f_date = film.get("publish_date", scheduled_date)

    if state.get(youtube_id, {}).get("status") == "done":
        log.info("[SKIP] %s — juz przetworzony", title)
        return True

    log.info("\n=== FILM: %s (%s) ===", title, youtube_id)
    film_state = state.get(youtube_id, {})

    try:
        # KROK 1: Generate SEO
        if not film_state.get("schema_data"):
            schema_data = run_generate(youtube_id, PORTAL_ID, headers)
            film_state["schema_data"] = schema_data
            state[youtube_id] = film_state
            save_state(state)
        else:
            log.info("  [1/5] SEO — z checkpointu")
            schema_data = film_state["schema_data"]

        # KROK 2: Inject WP
        if not film_state.get("wp_post_id"):
            wp_post_id, wp_url = run_inject(
                youtube_id, schema_data, PORTAL_ID, headers, f_status, f_date
            )
            film_state["wp_post_id"] = wp_post_id
            film_state["wp_url"] = wp_url
            state[youtube_id] = film_state
            save_state(state)
        else:
            log.info("  [2/5] Inject — z checkpointu")

        # KROK 3: YouTube update (nieblokujacy)
        if not film_state.get("yt_updated"):
            ok = run_yt_update(youtube_id, YT_CHANNEL_ID, schema_data, headers, f_date)
            film_state["yt_updated"] = ok
            state[youtube_id] = film_state
            save_state(state)
        else:
            log.info("  [3/5] YT update — z checkpointu")

        # KROK 4: Shorts candidates
        if not film_state.get("candidates"):
            candidates = run_shorts_candidates(youtube_id, PORTAL_ID, headers)
            film_state["candidates"] = candidates
            state[youtube_id] = film_state
            save_state(state)
        else:
            candidates = film_state["candidates"]
            log.info("  [4/5] Candidates — z checkpointu (%d)", len(candidates))

        # KROK 5: Render shorts
        if not film_state.get("render_jobs"):
            local_path = find_local_file(film)
            if local_path:
                log.info("  Znaleziono lokalny plik: %s", local_path)
            job_ids = run_shorts_render(youtube_id, candidates, PORTAL_ID, headers, local_path)
            film_state["render_jobs"] = job_ids
            state[youtube_id] = film_state
            save_state(state)
        else:
            log.info("  [5/5] Render — z checkpointu")

        film_state["status"] = "done"
        film_state["finished_at"] = datetime.now(tz=timezone.utc).isoformat()
        state[youtube_id] = film_state
        save_state(state)

        log.info("  ✅ DONE: prawy.pl -> %s", film_state.get("wp_url"))
        return True

    except Exception as e:
        log.error("  ❌ BLAD dla %s: %s", youtube_id, e)
        film_state["last_error"] = str(e)
        film_state["status"] = "error"
        film_state["failed_at"] = datetime.now(tz=timezone.utc).isoformat()
        state[youtube_id] = film_state
        save_state(state)
        return False

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="prawy-studio-worker — Studio Prawy_PL VSE pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Przyklady:
  python worker.py --single abc123 --date 2026-09-01 --status future
  python worker.py --batch films.json
  python worker.py --list
  python worker.py --shorts-only abc123
  python worker.py --check-captions abc123
  python worker.py --reset abc123
""",
    )
    parser.add_argument("--single", metavar="YOUTUBE_ID", help="Przetworz jeden film")
    parser.add_argument("--batch", metavar="FILMS_JSON", help="Przetworz filmy z pliku JSON")
    parser.add_argument("--list", action="store_true", help="Pokaz liste filmow i status")
    parser.add_argument("--shorts-only", metavar="YOUTUBE_ID", help="Generuj tylko shorty (bez regeneracji artykulu)")
    parser.add_argument("--check-captions", metavar="YOUTUBE_ID", help="Sprawdz gotowose napisow YT")
    parser.add_argument("--reset", metavar="YOUTUBE_ID", help="Reset checkpointu dla filmu")
    parser.add_argument("--date", metavar="YYYY-MM-DD", help="Data publikacji WP i YT (domyslnie: jutro)")
    parser.add_argument(
        "--status",
        choices=["draft", "future", "publish"],
        default=DEFAULT_POST_STATUS,
        help=f"Status postu WP (domyslnie: {DEFAULT_POST_STATUS})",
    )
    args = parser.parse_args()

    # Domyslna data: jutro
    scheduled_date = args.date or (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    state = load_state()

    # --- LIST ---
    if args.list:
        log.info("Lista filmow z checkpointu:")
        if not state:
            print("Brak zapisanego stanu.")
            return
        print(f"{'ID':15} {'Status':10} {'WP URL':50} {'Skonczony'}")
        for yt_id, s in state.items():
            print(f"{yt_id:15} {s.get('status','pending'):10} "
                  f"{str(s.get('wp_url','')):50} {s.get('finished_at','')}")
        return

    # --- RESET ---
    if args.reset:
        removed = state.pop(args.reset, None)
        save_state(state)
        if removed:
            log.info("Reset OK: %s", args.reset)
        else:
            log.warning("Nie znaleziono stanu dla: %s", args.reset)
        return

    # --- CHECK-CAPTIONS ---
    if args.check_captions:
        log.info("Generowanie tokenu...")
        token = generate_token()
        headers = auth_headers(token)
        ready = check_captions_ready(args.check_captions, headers, wait=True)
        if ready:
            log.info("✅ Napisy gotowe dla %s", args.check_captions)
        else:
            log.warning("❌ Napisy NIE gotowe dla %s (timeout)", args.check_captions)
        return

    # --- SHORTS-ONLY ---
    if args.shorts_only:
        youtube_id = args.shorts_only
        film_state = state.get(youtube_id, {})
        candidates = film_state.get("candidates")

        log.info("Generowanie tokenu...")
        token = generate_token()
        headers = auth_headers(token)

        if not candidates:
            log.info("Brak kandydatow w checkpoincie — generuje od nowa...")
            candidates = run_shorts_candidates(youtube_id, PORTAL_ID, headers)
            film_state["candidates"] = candidates
            state[youtube_id] = film_state
            save_state(state)

        local_path = find_local_file({"youtube_id": youtube_id})
        job_ids = run_shorts_render(youtube_id, candidates, PORTAL_ID, headers, local_path)
        film_state["render_jobs"] = job_ids
        state[youtube_id] = film_state
        save_state(state)
        log.info("✅ Shorts-only OK: %d job_ids", len(job_ids))
        return

    # --- SINGLE ---
    if args.single:
        youtube_id = args.single
        log.info("Generowanie tokenu...")
        token = generate_token()
        headers = auth_headers(token)

        # Weryfikacja napisow przed processingiem
        log.info("Weryfikacja gotowosci napisow...")
        captions_ok = check_captions_ready(youtube_id, headers, wait=True)
        if not captions_ok:
            log.warning("UWAGA: Napisy niedostepne — pipeline moze wygenerowac slabszy artykul")

        film = {"youtube_id": youtube_id, "title": youtube_id}
        process_film(film, state, headers, args.status, scheduled_date)
        return

    # --- BATCH ---
    if args.batch:
        batch_file = Path(args.batch)
        if not batch_file.exists():
            log.error("Plik batch nie istnieje: %s", batch_file)
            sys.exit(1)
        with open(batch_file, encoding="utf-8") as f:
            films = json.load(f)

        log.info("Generowanie tokenu...")
        token = generate_token()
        headers = auth_headers(token)

        ok_count = 0
        for i, film in enumerate(films):
            youtube_id = film["youtube_id"]
            log.info("Weryfikacja napisow dla %s...", youtube_id)
            captions_ok = check_captions_ready(youtube_id, headers, wait=False)
            if not captions_ok:
                log.warning("Napisy niedostepne dla %s — kontynuuje (moze byc slabszy wynik)", youtube_id)

            success = process_film(film, state, headers, args.status, scheduled_date)
            if success:
                ok_count += 1
            if i < len(films) - 1:
                log.info("Przerwa 20s przed kolejnym filmem...")
                time.sleep(20)

        log.info("\nBatch done: %d/%d OK", ok_count, len(films))
        return

    parser.print_help()


if __name__ == "__main__":
    main()
