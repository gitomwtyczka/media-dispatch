import subprocess, json, requests, sys, time, os
import datetime

# =====================================================================
# CONFIG — filmy 21.09.2026
# =====================================================================

FILMS = [
    {
        "yt_id": "Hsxu5L-27sU",
        "title": "Płużański Kołakowska Jankowski",
        "local_mp4": r"C:\Users\tomas2\Videos\Prawy\Płużański Kołakowska Jankowski.mp4",
    },
    {
        "yt_id": "vZAm46QIq84",
        "title": "Płużański Kołakowska Danuta",
        "local_mp4": r"C:\Users\tomas2\Videos\Prawy\Płużański Kołakowska Danuta.mp4",
    },
    {
        "yt_id": "-9y8AGJSNFs",
        "title": "Klimczak Woś 1",
        "local_mp4": r"C:\Users\tomas2\Videos\Prawy\Klimczak Woś 1.mp4",
    },
    {
        "yt_id": "lJLC8rqnlCs",
        "title": "Oskar Szafarowicz trybunał",
        "local_mp4": r"C:\Users\tomas2\Videos\Prawy\Oskar Szafarowicz trybunał.mp4",
    },
    {
        "yt_id": "PiwRUriZngc",
        "title": "Oskar Szafarowicz przegląd",
        "local_mp4": r"C:\Users\tomas2\Videos\Prawy\Oskar Szafarowicz przegląd.mp4",
    },
    {
        "yt_id": "J0Z1xMSqkls",
        "title": "Płużański Komuda Rozbiory 2",
        "local_mp4": r"C:\Users\tomas2\Videos\Prawy\Płużański Komuda Rozbiory_2..mp4",
    },
]

SSH_KEY = r"C:\Users\tomas2\.ssh\oracle-crimson.key"
VPS = "ubuntu@147.224.162.100"
VSE_BASE = "https://vse.impresjapr.pl"
PORTAL_ID = "2b047d7d-15a1-4d2f-8463-f89c2275bb73"
LOCAL_OVERRIDES = r"C:\ProgramData\VSELocalRunner\local_overrides.json"
SHORTS_OUTPUT = r"C:\VSE\Shorts"
RESULTS_PATH = r"C:\Users\tomas2\.gemini\antigravity\brain\prawy_21_09_2026_results.json"


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
           f'docker exec vse-api python3 -c "{code}"']
    r = subprocess.run(cmd, capture_output=True, timeout=30)
    token = r.stdout.decode('utf-8', errors='replace').strip()
    if not token:
        raise RuntimeError(f"JWT failed: {r.stderr.decode('utf-8','replace')[:200]}")
    print(f"[jwt] OK")
    return token


def vsh(token):
    return {"Authorization": f"Bearer {token}"}


def step_generate(yt_id, title, token):
    """VSE full pipeline: generate artykuł + opis YT. Zwraca (schema_data, transcript_ok)."""
    yt_url = f"https://www.youtube.com/watch?v={yt_id}"
    payload = {
        "video_url": yt_url,
        "publication_type": "full_analysis",  # NIE 'film'!
        "portal_id": PORTAL_ID,              # UUID, NIE string 'prawy'
        "post_title": title,
        "lang": "pl",
        "llm_provider": "claude"              # NIE 'gemini'!
    }
    print(f"  [generate] POST /v1/generate for {yt_id} '{title}'")
    r = requests.post(f"{VSE_BASE}/v1/generate", headers=vsh(token),
                      json=payload, timeout=360)
    print(f"  [generate] status={r.status_code}")
    if r.status_code != 200:
        print(f"  [generate] ERROR: {r.text[:300]}")
        return None, False

    resp = r.json()
    schema = resp.get("schema_data")
    transcript_ok = resp.get("transcript_available", True)
    if schema:
        transcript_ok = transcript_ok and schema.get("transcript_available", True)
    if not transcript_ok:
        print(f"  [generate] ⚠️ BRAK TRANSKRYPTU — hallucynacja! Pomijam inject.")
    else:
        print(f"  [generate] ✅ Transkrypt OK")
    return schema, transcript_ok


def step_inject(schema, yt_id, token):
    """Tworzy artykuł WP jako draft. Zwraca wp_post_id."""
    yt_url = f"https://www.youtube.com/watch?v={yt_id}"
    payload = {
        "video_url": yt_url,
        "schema_data": schema,
        "portal_id": PORTAL_ID,
        "post_status": "draft"  # ZAWSZE draft!
    }
    print(f"  [inject] POST /v1/inject")
    r = requests.post(f"{VSE_BASE}/v1/inject", headers=vsh(token),
                      json=payload, timeout=120)
    print(f"  [inject] status={r.status_code}: {r.text[:200]}")
    if r.status_code != 200:
        return None
    resp = r.json()
    return resp.get("wp_post_id") or resp.get("post_id")


def step_yt_desc_via_script(yt_id, schema, wp_post_id, token):
    """
    Aktualizuje opis YT przez yt_desc_fix.py wewnątrz kontenera.
    Powód: /v1/youtube/publish-description wymaga kanału który musi być właścicielem video.
    Prawy TV/Studio Prawy używa konta Tomasz Brzozowski — tylko ten token działa.
    """
    wp_url = f"https://prawy.pl/?p={wp_post_id}" if wp_post_id else ""

    # Budujemy opis ręcznie z schema_data
    lead = schema.get("lead", "")
    raw_chapters = schema.get("chapters", [])
    chapter_lines = [
        f"{c.get('time','')} {c.get('title','')}".strip()
        for c in raw_chapters if isinstance(c, dict)
    ]
    chapters_str = "\n".join(chapter_lines)
    tags = schema.get("tags", [])
    hashtags_str = " ".join(f"#{t}" if not t.startswith("#") else t for t in tags)
    desc = f"{lead}\n\n{chapters_str}\n\n{hashtags_str}"
    if wp_url:
        desc += f"\n\nCzytaj więcej: {wp_url}"

    # Skrypt do kontenera
    script_content = f"""import asyncio, sys, json
from api.db import AsyncSessionLocal
from api.models.youtube_channel import YouTubeChannel
from api.core.youtube_publish import _build_credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from sqlalchemy.future import select

VIDEO_ID = {json.dumps(yt_id)}
DESC = {json.dumps(desc)}

async def main():
    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(YouTubeChannel).where(YouTubeChannel.is_active == True)
        )
        channels = res.scalars().all()
        updated = False
        for ch in channels:
            try:
                creds = _build_credentials(ch)
                creds.refresh(Request())
                yt = build('youtube', 'v3', credentials=creds, cache_discovery=False)
                vresp = yt.videos().list(part='snippet', id=VIDEO_ID).execute()
                if not vresp.get('items'):
                    continue
                snippet = vresp['items'][0]['snippet']
                snippet['description'] = DESC
                yt.videos().update(part='snippet', body={{
                    'id': VIDEO_ID, 'snippet': snippet
                }}).execute()
                print(f'OK: updated {VIDEO_ID} via channel {{ch.title}}')
                updated = True
                break
            except Exception as e:
                print(f'SKIP channel {{ch.title}}: {{e}}')
        if not updated:
            print('FAILED: no channel could update', VIDEO_ID)

asyncio.run(main())
"""

    tmp_path = f"/tmp/yt_desc_{yt_id}.py"
    local_tmp = os.path.join(os.environ.get("TEMP", "C:\\Windows\\Temp"), f"yt_desc_{yt_id}.py")

    # Zapisz lokalnie, scp do kontenera, uruchom
    with open(local_tmp, 'w', encoding='utf-8') as f:
        f.write(script_content)

    scp_cmd = [
        "scp", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no",
        local_tmp, f"{VPS}:{tmp_path}"
    ]
    r = subprocess.run(scp_cmd, capture_output=True, timeout=30)
    if r.returncode != 0:
        print(f"  [yt_desc] SCP failed: {r.stderr.decode('utf-8','replace')[:200]}")
        return False

    run_cmd = [
        "ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no", VPS,
        f"docker cp {tmp_path} vse-api:/app/yt_desc_{yt_id}.py && "
        f"docker exec -w /app vse-api python3 yt_desc_{yt_id}.py"
    ]
    r2 = subprocess.run(run_cmd, capture_output=True, timeout=60)
    out = r2.stdout.decode('utf-8', errors='replace').strip()
    err = r2.stderr.decode('utf-8', errors='replace').strip()
    print(f"  [yt_desc] {out[:300]}")
    if err:
        print(f"  [yt_desc] stderr: {err[:200]}")
    return "OK:" in out


def update_local_overrides(films):
    """Aktualizuje local_overrides.json dla VSE Local Runner."""
    overrides = {}
    if os.path.exists(LOCAL_OVERRIDES):
        try:
            with open(LOCAL_OVERRIDES, 'r', encoding='utf-8') as f:
                overrides = json.load(f)
        except:
            pass
    for film in films:
        overrides[film['yt_id']] = film['local_mp4']
    os.makedirs(os.path.dirname(LOCAL_OVERRIDES), exist_ok=True)
    with open(LOCAL_OVERRIDES, 'w', encoding='utf-8') as f:
        json.dump(overrides, f, ensure_ascii=False, indent=2)
    print(f"[overrides] Updated: {list(overrides.keys())}")


def step_shorts_generate(film, token):
    """Wywołuje Short Machine /v1/shorts/generate. VSE sam tnie i zapisuje na dysku."""
    payload = {
        "youtube_url": f"https://www.youtube.com/watch?v={film['yt_id']}",
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
    print(f"  [shorts] POST /v1/shorts/generate for {film['yt_id']}")
    r = requests.post(f"{VSE_BASE}/v1/shorts/generate", headers=vsh(token),
                      json=payload, timeout=120)
    print(f"  [shorts] status={r.status_code}: {r.text[:300]}")
    if r.status_code == 200:
        return r.json()
    # Fallback minimal
    if r.status_code == 422:
        payload2 = {
            "youtube_url": f"https://www.youtube.com/watch?v={film['yt_id']}",
            "portal_id": PORTAL_ID,
            "count_emotional": 5,
            "count_professional": 5,
        }
        r2 = requests.post(f"{VSE_BASE}/v1/shorts/generate", headers=vsh(token),
                           json=payload2, timeout=120)
        print(f"  [shorts-minimal] status={r2.status_code}: {r2.text[:300]}")
        if r2.status_code == 200:
            return r2.json()
    return None


# =====================================================================
# MAIN
# =====================================================================

def main():
    print("=" * 70)
    print(f"prawy_21_09_2026_pipeline.py — start {datetime.datetime.now()}")
    print(f"Films: {[f['title'] for f in FILMS]}")
    print("=" * 70)

    # 0. JWT
    token = get_jwt()

    # 1. Aktualizuj local_overrides dla Short Machine
    update_local_overrides(FILMS)

    results = []

    for film in FILMS:
        print(f"\n{'='*60}")
        print(f"FILM: {film['title']} | YT: {film['yt_id']}")
        print(f"{'='*60}")
        result = {
            "yt_id": film["yt_id"],
            "title": film["title"],
            "wp_post_id": None,
            "wp_draft_url": None,
            "yt_desc_ok": False,
            "shorts_queued": False,
            "status": "PENDING"
        }

        # --- KROK 1: VSE generate ---
        schema, transcript_ok = step_generate(film["yt_id"], film["title"], token)

        if not transcript_ok:
            result["status"] = "WAIT_FOR_TRANSCRIPT"
            result["note"] = "Brak transkryptu — ponów za 30 min"
            results.append(result)
            continue

        if schema is None:
            result["status"] = "GENERATE_FAILED"
            results.append(result)
            continue

        # --- KROK 2: WP inject (draft) ---
        wp_id = step_inject(schema, film["yt_id"], token)
        result["wp_post_id"] = wp_id
        if wp_id:
            result["wp_draft_url"] = f"https://prawy.pl/?p={wp_id}"
            print(f"  [inject] ✅ WP draft #{wp_id}")
        else:
            print(f"  [inject] ⚠️ Brak wp_post_id")

        # --- KROK 3: YT description update ---
        yt_ok = step_yt_desc_via_script(film["yt_id"], schema, wp_id, token)
        result["yt_desc_ok"] = yt_ok
        print(f"  [yt_desc] {'✅ OK' if yt_ok else '❌ FAILED'}")

        # --- KROK 4: Short Machine generate ---
        shorts_resp = step_shorts_generate(film, token)
        result["shorts_queued"] = shorts_resp is not None
        result["shorts_response"] = shorts_resp
        print(f"  [shorts] {'✅ Queued' if shorts_resp else '❌ FAILED'}")

        result["status"] = "OK" if (wp_id or yt_ok or shorts_resp) else "FAILED"
        results.append(result)

        # Przerwa między filmami (nie bombuj API)
        print(f"  [pause] 10s...")
        time.sleep(10)

    # Podsumowanie
    print("\n" + "=" * 70)
    print("PODSUMOWANIE")
    print("=" * 70)
    for r in results:
        st = r['status']
        wp = r.get('wp_post_id', '-')
        yt = '✅' if r.get('yt_desc_ok') else '❌'
        sh = '✅' if r.get('shorts_queued') else '❌'
        print(f"  {r['title']:<40} WP:{wp} YT:{yt} Shorts:{sh} [{st}]")

    # Zapisz wyniki
    with open(RESULTS_PATH, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n[done] Wyniki: {RESULTS_PATH}")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
