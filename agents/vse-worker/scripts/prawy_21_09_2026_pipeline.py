import subprocess, json, requests, sys, time, os
import datetime

# =====================================================================
# CONFIG — filmy 21.09.2026
# UWAGA: Film 1 (Jankowski) ma juz WP draft #126808 — pomijamy generate+inject
# =====================================================================

FILMS_FULL = [
    {
        "yt_id": "vZAm46QIq84",
        "title": "Pluzanski Kolkowska Danuta",
        "local_mp4": r"C:\Users\tomas2\Videos\Prawy\P\u0142u\u017ca\u0144ski Ko\u0142akowska Danuta.mp4",
    },
    {
        "yt_id": "-9y8AGJSNFs",
        "title": "Klimczak Wos 1",
        "local_mp4": r"C:\Users\tomas2\Videos\Prawy\Klimczak Wo\u015b 1.mp4",
    },
    {
        "yt_id": "lJLC8rqnlCs",
        "title": "Oskar Szafarowicz trybunal",
        "local_mp4": r"C:\Users\tomas2\Videos\Prawy\Oskar Szafarowicz trybuna\u0142.mp4",
    },
    {
        "yt_id": "PiwRUriZngc",
        "title": "Oskar Szafarowicz przeglad",
        "local_mp4": r"C:\Users\tomas2\Videos\Prawy\Oskar Szafarowicz przegl\u0105d.mp4",
    },
    {
        "yt_id": "J0Z1xMSqkls",
        "title": "Pluzanski Komuda Rozbiory 2",
        "local_mp4": r"C:\Users\tomas2\Videos\Prawy\P\u0142u\u017ca\u0144ski Komuda Rozbiory_2..mp4",
    },
]

# Film 1 Jankowski - tylko YT desc + shorts (WP draft #126808 juz istnieje)
FILM_JANKOWSKI = {
    "yt_id": "Hsxu5L-27sU",
    "title": "Pluzanski Kolakowska Jankowski",
    "local_mp4": r"C:\Users\tomas2\Videos\Prawy\P\u0142u\u017ca\u0144ski Ko\u0142akowska Jankowski.mp4",
    "wp_post_id": 126808,
}

SSH_KEY = r"C:\Users\tomas2\.ssh\oracle-crimson.key"
VPS = "ubuntu@147.224.162.100"
VSE_BASE = "https://vse.impresjapr.pl"
PORTAL_ID = "2b047d7d-15a1-4d2f-8463-f89c2275bb73"
LOCAL_OVERRIDES = r"C:\ProgramData\VSELocalRunner\local_overrides.json"
SHORTS_OUTPUT = r"C:\VSE\Shorts"
RESULTS_PATH = r"C:\Users\tomas2\.gemini\antigravity\brain\prawy_21_09_2026_results.json"
ALL_FILMS = [FILM_JANKOWSKI] + FILMS_FULL


# =====================================================================
# HELPERS
# =====================================================================

def get_jwt():
    code = (
        "import os, datetime; from jose import jwt; "
        "s=os.environ.get('JWT_SECRET_KEY',''); "
        "p={'sub':'4b97ab0c-98ee-46c6-9be8-d86adc4cb38a','exp':datetime.datetime.utcnow()+datetime.timedelta(hours=24)}; "
        "print(jwt.encode(p,s,algorithm='HS256'))"
    )
    cmd = ["ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no", VPS,
           "docker exec vse-api python3 -c " + repr(code)]
    r = subprocess.run(cmd, capture_output=True, timeout=30)
    token = r.stdout.decode('utf-8', errors='replace').strip()
    if not token:
        raise RuntimeError("JWT failed: " + r.stderr.decode('utf-8','replace')[:200])
    print("[jwt] OK")
    return token


def vsh(token):
    return {"Authorization": "Bearer " + token}


def step_generate(yt_id, title, token):
    """VSE generate. Zwraca (schema_data, transcript_ok)."""
    yt_url = "https://www.youtube.com/watch?v=" + yt_id
    payload = {
        "video_url": yt_url,
        "publication_type": "full_analysis",
        "portal_id": PORTAL_ID,
        "post_title": title,
        "lang": "pl",
        "llm_provider": "claude"
    }
    print("  [generate] POST /v1/generate for " + yt_id + " '" + title + "'")
    r = requests.post(VSE_BASE + "/v1/generate", headers=vsh(token),
                      json=payload, timeout=360)
    print("  [generate] status=" + str(r.status_code))
    if r.status_code != 200:
        print("  [generate] ERROR: " + r.text[:300])
        return None, False
    resp = r.json()
    schema = resp.get("schema_data")
    transcript_ok = resp.get("transcript_available", True)
    if schema:
        transcript_ok = transcript_ok and schema.get("transcript_available", True)
    if not transcript_ok:
        print("  [generate] BRAK TRANSKRYPTU - hallucynacja! Pomijam inject.")
    else:
        print("  [generate] Transkrypt OK")
    return schema, transcript_ok


def step_inject(schema, yt_id, token):
    """Tworzy artykul WP jako draft. Zwraca wp_post_id."""
    yt_url = "https://www.youtube.com/watch?v=" + yt_id
    payload = {
        "video_url": yt_url,
        "schema_data": schema,
        "portal_id": PORTAL_ID,
        "post_status": "draft"
    }
    print("  [inject] POST /v1/inject")
    r = requests.post(VSE_BASE + "/v1/inject", headers=vsh(token),
                      json=payload, timeout=120)
    print("  [inject] status=" + str(r.status_code) + ": " + r.text[:200])
    if r.status_code != 200:
        return None
    resp = r.json()
    return resp.get("wp_post_id") or resp.get("post_id")


def step_yt_desc_via_script(yt_id, schema, wp_post_id, token):
    """
    Aktualizuje opis YT przez skrypt w kontenerze vse-api.
    Uzywa konta Tomasz Brzozowski (jedyne ktore moze edytowac Prawy TV).
    UWAGA: NIE uzywa f-stringow w script_content zeby uniknac NameError!
    """
    wp_url = "https://prawy.pl/?p=" + str(wp_post_id) if wp_post_id else ""

    lead = schema.get("lead", "")
    raw_chapters = schema.get("chapters", [])
    chapter_lines = [
        (c.get('time', '') + " " + c.get('title', '')).strip()
        for c in raw_chapters if isinstance(c, dict)
    ]
    chapters_str = "\n".join(chapter_lines)
    tags = schema.get("tags", [])
    hashtags_str = " ".join(("#" + t) if not t.startswith("#") else t for t in tags)
    desc = lead + "\n\n" + chapters_str + "\n\n" + hashtags_str
    if wp_url:
        desc += "\n\nCzytaj wiecej: " + wp_url

    # Buduj script_content BEZ f-stringow - unikamy NameError z zagniezdzonymi {}
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
        "DESC = " + json.dumps(desc),
        "",
        "async def main():",
        "    async with AsyncSessionLocal() as db:",
        "        res = await db.execute(",
        "            select(YouTubeChannel).where(YouTubeChannel.is_active == True)",
        "        )",
        "        channels = res.scalars().all()",
        "        updated = False",
        "        for ch in channels:",
        "            try:",
        "                creds = _build_credentials(ch)",
        "                creds.refresh(Request())",
        "                yt = build('youtube', 'v3', credentials=creds, cache_discovery=False)",
        "                vresp = yt.videos().list(part='snippet', id=VIDEO_ID).execute()",
        "                if not vresp.get('items'):",
        "                    continue",
        "                snippet = vresp['items'][0]['snippet']",
        "                snippet['description'] = DESC",
        "                yt.videos().update(part='snippet', body={'id': VIDEO_ID, 'snippet': snippet}).execute()",
        "                print('OK: updated ' + VIDEO_ID + ' via ' + str(ch.title))",
        "                updated = True",
        "                break",
        "            except Exception as e:",
        "                print('SKIP ' + str(ch.title) + ': ' + str(e))",
        "        if not updated:",
        "            print('FAILED: no channel updated ' + VIDEO_ID)",
        "",
        "asyncio.run(main())",
    ]
    script_content = "\n".join(script_lines)

    tmp_path = "/tmp/yt_desc_" + yt_id.replace("-", "_") + ".py"
    local_tmp = os.path.join(os.environ.get("TEMP", "C:\\Windows\\Temp"),
                             "yt_desc_" + yt_id.replace("-", "_") + ".py")

    with open(local_tmp, 'w', encoding='utf-8') as f:
        f.write(script_content)

    scp_cmd = [
        "scp", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no",
        local_tmp, VPS + ":" + tmp_path
    ]
    r = subprocess.run(scp_cmd, capture_output=True, timeout=30)
    if r.returncode != 0:
        print("  [yt_desc] SCP failed: " + r.stderr.decode('utf-8','replace')[:200])
        return False

    script_name = "yt_desc_" + yt_id.replace("-", "_") + ".py"
    run_cmd = [
        "ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no", VPS,
        "docker cp " + tmp_path + " vse-api:/app/" + script_name +
        " && docker exec -w /app vse-api python3 " + script_name
    ]
    r2 = subprocess.run(run_cmd, capture_output=True, timeout=60)
    out = r2.stdout.decode('utf-8', errors='replace').strip()
    err = r2.stderr.decode('utf-8', errors='replace').strip()
    print("  [yt_desc] " + out[:300])
    if err:
        print("  [yt_desc] stderr: " + err[:200])
    return "OK:" in out


def update_local_overrides(films):
    """Aktualizuje local_overrides.json dla VSE Local Runner."""
    overrides = {}
    if os.path.exists(LOCAL_OVERRIDES):
        try:
            with open(LOCAL_OVERRIDES, 'r', encoding='utf-8') as f:
                overrides = json.load(f)
        except Exception:
            pass
    for film in films:
        overrides[film['yt_id']] = film['local_mp4']
    os.makedirs(os.path.dirname(LOCAL_OVERRIDES), exist_ok=True)
    with open(LOCAL_OVERRIDES, 'w', encoding='utf-8') as f:
        json.dump(overrides, f, ensure_ascii=False, indent=2)
    print("[overrides] Updated: " + str(list(overrides.keys())))


def step_shorts_generate(film, token):
    """Short Machine /v1/shorts/generate. VSE kolejkuje, Local Runner tnie MP4."""
    payload = {
        "youtube_url": "https://www.youtube.com/watch?v=" + film['yt_id'],
        "youtube_id": film['yt_id'],
        "portal_id": PORTAL_ID,
        "count_emotional": 5,
        "count_professional": 5,
        "local_path": film['local_mp4'],
        "render_config": {
            "format": "9:16",
            "output_dir": SHORTS_OUTPUT
        }
    }
    print("  [shorts] POST /v1/shorts/generate for " + film['yt_id'])
    r = requests.post(VSE_BASE + "/v1/shorts/generate", headers=vsh(token),
                      json=payload, timeout=120)
    print("  [shorts] status=" + str(r.status_code) + ": " + r.text[:300])
    if r.status_code == 200:
        return r.json()
    if r.status_code == 422:
        payload2 = {
            "youtube_url": "https://www.youtube.com/watch?v=" + film['yt_id'],
            "portal_id": PORTAL_ID,
            "count_emotional": 5,
            "count_professional": 5,
        }
        r2 = requests.post(VSE_BASE + "/v1/shorts/generate", headers=vsh(token),
                           json=payload2, timeout=120)
        print("  [shorts-minimal] status=" + str(r2.status_code) + ": " + r2.text[:300])
        if r2.status_code == 200:
            return r2.json()
    return None


# =====================================================================
# MAIN
# =====================================================================

def main():
    print("=" * 70)
    print("prawy_21_09_2026_pipeline.py (v2) start " + str(datetime.datetime.now()))
    print("=" * 70)

    token = get_jwt()
    update_local_overrides(ALL_FILMS)

    results = []

    # ----------------------------------------------------------------
    # Film 1: Jankowski - juz ma WP draft #126808, pomijamy generate+inject
    # ----------------------------------------------------------------
    print("\n" + "=" * 60)
    print("FILM: Jankowski (WP draft #126808 juz istnieje) | YT: Hsxu5L-27sU")
    print("=" * 60)

    j = FILM_JANKOWSKI
    result_j = {
        "yt_id": j["yt_id"], "title": j["title"],
        "wp_post_id": j["wp_post_id"],
        "wp_draft_url": "https://prawy.pl/?p=" + str(j["wp_post_id"]),
        "yt_desc_ok": False, "shorts_queued": False, "status": "PARTIAL"
    }

    # Pobierz schema z DB zeby zbudowac opis YT
    cmd_db = [
        "ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no", VPS,
        "docker exec vse-postgres psql -U vse -d vse -t -c "
        "\"SELECT schema_data::text FROM transcript_jobs WHERE video_url LIKE '%Hsxu5L-27sU%' ORDER BY created_at DESC LIMIT 1;\""
    ]
    r_db = subprocess.run(cmd_db, capture_output=True, timeout=30)
    schema_j = None
    db_out = r_db.stdout.decode('utf-8', errors='replace').strip()
    # Wyciagnij JSON
    for line in db_out.split('\n'):
        line = line.strip()
        if line.startswith('{'):
            try:
                schema_j = json.loads(line)
                break
            except Exception:
                pass

    if schema_j:
        print("  [db] Schema OK dla Jankowski")
        yt_ok_j = step_yt_desc_via_script(j["yt_id"], schema_j, j["wp_post_id"], token)
        result_j["yt_desc_ok"] = yt_ok_j
    else:
        print("  [db] BRAK schema dla Jankowski - pomijam YT desc")

    shorts_j = step_shorts_generate(j, token)
    result_j["shorts_queued"] = shorts_j is not None
    result_j["status"] = "OK" if result_j["yt_desc_ok"] or result_j["shorts_queued"] else "PARTIAL"
    results.append(result_j)
    time.sleep(10)

    # ----------------------------------------------------------------
    # Filmy 2-6: pelny pipeline
    # ----------------------------------------------------------------
    for film in FILMS_FULL:
        print("\n" + "=" * 60)
        print("FILM: " + film['title'] + " | YT: " + film['yt_id'])
        print("=" * 60)
        result = {
            "yt_id": film["yt_id"], "title": film["title"],
            "wp_post_id": None, "wp_draft_url": None,
            "yt_desc_ok": False, "shorts_queued": False, "status": "PENDING"
        }

        schema, transcript_ok = step_generate(film["yt_id"], film["title"], token)

        if not transcript_ok:
            result["status"] = "WAIT_FOR_TRANSCRIPT"
            result["note"] = "Brak transkryptu - ponow za 30 min"
            results.append(result)
            continue

        if schema is None:
            result["status"] = "GENERATE_FAILED"
            results.append(result)
            continue

        wp_id = step_inject(schema, film["yt_id"], token)
        result["wp_post_id"] = wp_id
        if wp_id:
            result["wp_draft_url"] = "https://prawy.pl/?p=" + str(wp_id)
            print("  [inject] WP draft #" + str(wp_id))

        yt_ok = step_yt_desc_via_script(film["yt_id"], schema, wp_id, token)
        result["yt_desc_ok"] = yt_ok
        print("  [yt_desc] " + ("OK" if yt_ok else "FAILED"))

        shorts_resp = step_shorts_generate(film, token)
        result["shorts_queued"] = shorts_resp is not None
        print("  [shorts] " + ("Queued" if shorts_resp else "FAILED"))

        result["status"] = "OK" if (wp_id or yt_ok or shorts_resp) else "FAILED"
        results.append(result)

        print("  [pause] 10s...")
        time.sleep(10)

    # ----------------------------------------------------------------
    # Podsumowanie
    # ----------------------------------------------------------------
    print("\n" + "=" * 70)
    print("PODSUMOWANIE")
    print("=" * 70)
    for r in results:
        wp = str(r.get('wp_post_id', '-'))
        yt = "OK" if r.get('yt_desc_ok') else "--"
        sh = "OK" if r.get('shorts_queued') else "--"
        print("  " + r['title'][:38].ljust(38) + " WP:" + wp.ljust(7) + " YT:" + yt + " Shorts:" + sh + " [" + r['status'] + "]")

    with open(RESULTS_PATH, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\n[done] Wyniki: " + RESULTS_PATH)
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
