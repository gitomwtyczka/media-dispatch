#!/usr/bin/env python3
"""
prawy_yt_fix_21_09_2026.py — Pipeline naprawczy YT title + desc dla 6 filmow (21.09.2026)

Kontekst:
- 6 filmow ma juz utworzone drafty WP (#126808, #126813, #126818, #126823, #126828, #126833)
- Wymagana aktualizacja tytulu i opisu YouTube API v3 (pelny snippet: title + description + categoryId)
- youtube_description_body pobierane z LIVE response POST /v1/generate (nie istnieje w DB)
- Skrypt w kontenerze budowany jako lista linii (brak zagniezdzonych f-stringow)
- Kanaly aktywne: Studio Prawy_PL i Prawy TV (skip Tomasz Brzozowski i VeriNarrMundo)
"""

import os
import sys
import json
import time
import tempfile
import datetime
import subprocess
import requests

# =====================================================================
# CONFIG
# =====================================================================

VPS = "ubuntu@147.224.162.100"
SSH_KEY = r"C:\Users\tomas2\.ssh\oracle-crimson.key"
VSE_BASE = "https://vse.impresjapr.pl"
PORTAL_ID = "2b047d7d-15a1-4d2f-8463-f89c2275bb73"
USER_ID = "4b97ab0c-98ee-46c6-9be8-d86adc4cb38a"
RESULTS_PATH = r"C:\Users\tomas2\.gemini\antigravity\brain\yt_fix_results.json"

FILMS = [
    {
        "yt_id": "Hsxu5L-27sU",
        "title": "Pluzanski Kolakowska Jankowski",
        "wp_post_id": 126808,
        "local_mp4": r"C:\Users\tomas2\Videos\Prawy\Pluzanski Kolakowska Jankowski.mp4",
    },
    {
        "yt_id": "vZAm46QIq84",
        "title": "Pluzanski Kolakowska Danuta",
        "wp_post_id": 126813,
        "local_mp4": r"C:\Users\tomas2\Videos\Prawy\Pluzanski Kolakowska Danuta.mp4",
    },
    {
        "yt_id": "-9y8AGJSNFs",
        "title": "Klimczak Wos 1",
        "wp_post_id": 126818,
        "local_mp4": r"C:\Users\tomas2\Videos\Prawy\Klimczak Wos 1.mp4",
    },
    {
        "yt_id": "lJLC8rqnlCs",
        "title": "Oskar Szafarowicz trybunal",
        "wp_post_id": 126823,
        "local_mp4": r"C:\Users\tomas2\Videos\Prawy\Oskar Szafarowicz trybunal.mp4",
    },
    {
        "yt_id": "PiwRUriZngc",
        "title": "Oskar Szafarowicz przeglad",
        "wp_post_id": 126828,
        "local_mp4": r"C:\Users\tomas2\Videos\Prawy\Oskar Szafarowicz przeglad.mp4",
    },
    {
        "yt_id": "J0Z1xMSqkls",
        "title": "Pluzanski Komuda Rozbiory 2",
        "wp_post_id": 126833,
        "local_mp4": r"C:\Users\tomas2\Videos\Prawy\Pluzanski Komuda Rozbiory 2.mp4",
    },
]

# =====================================================================
# HELPERS
# =====================================================================

def get_jwt():
    """Generuje poprawny token JWT przez jose.jwt.encode w kontenerze vse-api."""
    code = (
        "import os, datetime; from jose import jwt; "
        "s=os.environ.get('JWT_SECRET_KEY',''); "
        "p={'sub':'4b97ab0c-98ee-46c6-9be8-d86adc4cb38a','exp':datetime.datetime.utcnow()+datetime.timedelta(hours=24)}; "
        "print(jwt.encode(p,s,algorithm='HS256'))"
    )
    cmd = [
        "ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no", VPS,
        "docker exec vse-api python3 -c " + repr(code)
    ]
    r = subprocess.run(cmd, capture_output=True, timeout=30)
    token = r.stdout.decode("utf-8", errors="replace").strip()
    if not token:
        err = r.stderr.decode("utf-8", errors="replace")[:200]
        raise RuntimeError("JWT generation failed: " + err)
    print("[JWT] Token wygenerowany pomyslnie")
    return token


def vsh(token):
    return {"Authorization": "Bearer " + token}


def step_generate_metadata(film, token):
    """
    Wywoluje POST /v1/generate aby uzyskac live response z polami:
    youtube_description_body oraz post_title / seo_title.
    """
    yt_id = film["yt_id"]
    title = film["title"]
    yt_url = "https://www.youtube.com/watch?v=" + yt_id
    payload = {
        "video_url": yt_url,
        "publication_type": "full_analysis",
        "portal_id": PORTAL_ID,
        "post_title": title,
        "lang": "pl",
        "llm_provider": "claude",
    }
    print("  [generate] POST /v1/generate dla " + yt_id + " (" + title + ")")
    try:
        r = requests.post(
            VSE_BASE + "/v1/generate",
            headers=vsh(token),
            json=payload,
            timeout=360,
        )
        print("  [generate] status=" + str(r.status_code))
        if r.status_code != 200:
            print("  [generate] BLAD HTTP: " + r.text[:300])
            return None, None

        resp = r.json()
        schema = resp.get("schema_data") or {}

        # 1. Tytul YT (snippet['title'] jest wymagany przez YouTube API v3!)
        yt_title = (
            schema.get("post_title")
            or schema.get("title")
            or schema.get("yt_title")
            or resp.get("post_title")
            or title
        )
        # Obetnij do max 100 znakow (limit YouTube)
        if len(yt_title) > 100:
            yt_title = yt_title[:97] + "..."

        # 2. Opis YT (live response ma youtube_description_body)
        yt_desc = (
            schema.get("youtube_description_body")
            or resp.get("youtube_description_body")
        )

        # Fallback jesli pole youtube_description_body bylo puste
        if not yt_desc:
            print("  [generate] Brak youtube_description_body w live response — buduje z lead+chapters+tags")
            lead = schema.get("lead", "")
            raw_chapters = schema.get("chapters", [])
            chapter_lines = [
                (str(c.get("time", "")) + " " + str(c.get("title", ""))).strip()
                for c in raw_chapters
                if isinstance(c, dict)
            ]
            chapters_str = "\n".join(chapter_lines)
            tags = schema.get("tags", [])
            hashtags_str = " ".join(
                ("#" + str(t)) if not str(t).startswith("#") else str(t)
                for t in tags
            )
            parts = [p for p in [lead, chapters_str, hashtags_str] if p]
            if film.get("wp_post_id"):
                parts.append("Czytaj wiecej: https://prawy.pl/?p=" + str(film["wp_post_id"]))
            yt_desc = "\n\n".join(parts)
        elif film.get("wp_post_id") and ("prawy.pl/?p=" + str(film["wp_post_id"])) not in yt_desc:
            yt_desc += "\n\nCzytaj wiecej: https://prawy.pl/?p=" + str(film["wp_post_id"])

        print("  [generate] Metadata OK — Title (" + str(len(yt_title)) + " zn.): " + yt_title[:60] + "...")
        print("  [generate] Opis (" + str(len(yt_desc)) + " zn.): " + yt_desc[:80].replace("\n", " ") + "...")
        return yt_title, yt_desc

    except Exception as e:
        print("  [generate] Wyjatek: " + str(e))
        return None, None


def build_container_script(yt_id, yt_title, yt_desc):
    """
    Buduje skrypt Pythona do wykonania w kontenerze vse-api.
    BEZ f-stringow (unikanie NameError), lista linii + '\n'.join().
    Filtruje kanaly TYLKO do Studio Prawy_PL i Prawy TV.
    """
    script_lines = [
        "import asyncio, json",
        "from api.db import AsyncSessionLocal",
        "from api.models.youtube_channel import YouTubeChannel",
        "from api.core.youtube_publish import _build_credentials",
        "from google.auth.transport.requests import Request",
        "from googleapiclient.discovery import build",
        "from sqlalchemy.future import select",
        "",
        "VIDEO_ID = " + json.dumps(yt_id),
        "YT_TITLE = " + json.dumps(yt_title),
        "YT_DESC = " + json.dumps(yt_desc),
        "PRAWY_CHANNELS = ['UCoH2G9By4OX3kcLsc8lHgDw', 'UCNXh5eIlMVxnUBpTMKUp4CA']",
        "",
        "async def main():",
        "    async with AsyncSessionLocal() as db:",
        "        res = await db.execute(select(YouTubeChannel).where(YouTubeChannel.is_active == True))",
        "        channels = res.scalars().all()",
        "        updated = False",
        "        for ch in channels:",
        "            if ch.youtube_channel_id not in PRAWY_CHANNELS:",
        "                print('SKIP non-prawy: ' + str(ch.title))",
        "                continue",
        "            try:",
        "                creds = _build_credentials(ch)",
        "                creds.refresh(Request())",
        "                yt = build('youtube', 'v3', credentials=creds, cache_discovery=False)",
        "                vresp = yt.videos().list(part='snippet', id=VIDEO_ID).execute()",
        "                if not vresp.get('items'):",
        "                    print('NOT FOUND on channel: ' + str(ch.title))",
        "                    continue",
        "                snippet = vresp['items'][0]['snippet']",
        "                snippet['title'] = YT_TITLE",
        "                snippet['description'] = YT_DESC",
        "                yt.videos().update(part='snippet', body={'id': VIDEO_ID, 'snippet': snippet}).execute()",
        "                print('OK: ' + VIDEO_ID + ' via ' + str(ch.title))",
        "                updated = True",
        "                break",
        "            except Exception as e:",
        "                print('SKIP ' + str(ch.title) + ': ' + str(e)[:100])",
        "        if not updated:",
        "            print('FAILED: ' + VIDEO_ID)",
        "",
        "asyncio.run(main())",
    ]
    return "\n".join(script_lines)


def run_in_container(script_content, script_name, yt_id):
    """
    Zapisuje skrypt lokalnie w temp, wysyla scp na VPS, kopiuje docker cp do vse-api i wykonuje.
    """
    tmp_local = os.path.join(tempfile.gettempdir(), script_name)
    with open(tmp_local, "w", encoding="utf-8") as f:
        f.write(script_content)

    tmp_vps = "/tmp/" + script_name
    scp = [
        "scp", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no",
        tmp_local, VPS + ":" + tmp_vps
    ]
    r = subprocess.run(scp, capture_output=True, timeout=30)
    if r.returncode != 0:
        err = r.stderr.decode("utf-8", errors="replace")[:200]
        return False, "SCP failed: " + err

    run = [
        "ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no", VPS,
        "docker cp " + tmp_vps + " vse-api:/app/" + script_name +
        " && docker exec -w /app vse-api python3 " + script_name
    ]
    r2 = subprocess.run(run, capture_output=True, timeout=90)
    out = r2.stdout.decode("utf-8", errors="replace").strip()
    return "OK:" in out, out


# =====================================================================
# MAIN
# =====================================================================

def main():
    print("=" * 70)
    print("prawy_yt_fix_21_09_2026.py start: " + str(datetime.datetime.now()))
    print("=" * 70)

    token = get_jwt()
    results = []

    for idx, film in enumerate(FILMS, 1):
        yt_id = film["yt_id"]
        title = film["title"]
        wp_post_id = film["wp_post_id"]
        print("\n" + "-" * 60)
        print("[" + str(idx) + "/6] " + title + " | YT: " + yt_id + " | WP: #" + str(wp_post_id))
        print("-" * 60)

        film_res = {
            "yt_id": yt_id,
            "title": title,
            "wp_post_id": wp_post_id,
            "yt_title": None,
            "yt_desc_length": 0,
            "yt_update_ok": False,
            "exec_output": None,
            "status": "PENDING"
        }

        # Krok 1: Wygeneruj swieze metadane SEO z /v1/generate
        yt_title, yt_desc = step_generate_metadata(film, token)
        if not yt_title or not yt_desc:
            film_res["status"] = "GENERATE_FAILED"
            results.append(film_res)
            print("  [STOP] Nie udalo sie pobrac metadanych z /v1/generate")
            continue

        film_res["yt_title"] = yt_title
        film_res["yt_desc_length"] = len(yt_desc)

        # Krok 2: Zbuduj skrypt kontenera i zaktualizuj YouTube
        script_name = "yt_fix_" + yt_id.replace("-", "_") + ".py"
        script_content = build_container_script(yt_id, yt_title, yt_desc)

        print("  [exec] Wgrywanie i uruchamianie w vse-api: " + script_name)
        ok, out = run_in_container(script_content, script_name, yt_id)
        film_res["yt_update_ok"] = ok
        film_res["exec_output"] = out
        film_res["status"] = "OK" if ok else "YT_UPDATE_FAILED"

        print("  [result] " + ("SUKCES" if ok else "BLAD") + " -> " + out[:250])
        results.append(film_res)

        print("  [pause] Odczekuje 5s...")
        time.sleep(5)

    # Podsumowanie i zapis
    print("\n" + "=" * 70)
    print("PODSUMOWANIE NAPRAWY YT TITLE+DESC")
    print("=" * 70)
    for r in results:
        status_tag = "[" + r["status"] + "]"
        print("  " + r["yt_id"] + " | " + r["title"][:30].ljust(30) + " | WP: #" + str(r["wp_post_id"]).ljust(8) + " | " + status_tag)

    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n[ZAPIS] Wyniki zapisano w: " + RESULTS_PATH)


if __name__ == "__main__":
    main()
