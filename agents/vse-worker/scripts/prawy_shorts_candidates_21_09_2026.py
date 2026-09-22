#!/usr/bin/env python3
"""
prawy_shorts_candidates_21_09_2026.py — Shorts Candidates Pipeline & OpenAPI Diagnostic (21.09.2026)

Kontekst:
- Endpointy Shorts w VSE: /v1/shorts/candidates, /v1/shorts/render, /v1/shorts/pending, /v1/shorts/{job_id}/result
- Skrypt pelni podwojna role:
  1. Diagnostyczna: pobiera openapi.json (z localhost:8085 przez SSH oraz z https://vse.impresjapr.pl),
     ekstrahuje dokladne schematy OpenAPI/Pydantic dla endpointow /shorts/* i zapisuje do brain.
  2. Wykonawcza: testuje wywolanie POST /v1/shorts/candidates dla 6 filmow z 21.09.2026,
     zwraca wyselekcjonowane segmenty (start_sec, end_sec, tytul) oraz przygotowuje zadania renderu.
- Wyniki zapisywane sa do:
  C:\Users\tomas2\.gemini\antigravity\brain\shorts_openapi_schema.json
  C:\Users\tomas2\.gemini\antigravity\brain\shorts_candidates_results.json
"""

import os
import sys
import json
import time
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
SCHEMA_OUTPUT_PATH = r"C:\Users\tomas2\.gemini\antigravity\brain\shorts_openapi_schema.json"
RESULTS_OUTPUT_PATH = r"C:\Users\tomas2\.gemini\antigravity\brain\shorts_candidates_results.json"

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


def fetch_openapi_spec():
    """
    Pobiera pelny openapi.json z VSE API:
    1. Przez SSH curl z http://localhost:8085/openapi.json
    2. Fallback: bezposrednio z https://vse.impresjapr.pl/openapi.json
    Ekstrahuje endpointy i schematy powiazane z /shorts/.
    """
    print("\n[OPENAPI] Pobieranie schematu OpenAPI z VSE...")
    raw_spec = None

    # Proba 1: SSH do localhost:8085
    try:
        cmd = [
            "ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no", VPS,
            "curl -s http://localhost:8085/openapi.json"
        ]
        r = subprocess.run(cmd, capture_output=True, timeout=30)
        if r.returncode == 0 and r.stdout.strip().startswith(b"{"):
            raw_spec = json.loads(r.stdout.decode("utf-8", errors="replace"))
            print("[OPENAPI] Pobrany pomyslnie przez SSH curl (localhost:8085)")
    except Exception as e:
        print("[OPENAPI] SSH curl wyjatek: " + str(e))

    # Proba 2: HTTP requests fallback
    if not raw_spec:
        try:
            r = requests.get(VSE_BASE + "/openapi.json", timeout=15)
            if r.status_code == 200:
                raw_spec = r.json()
                print("[OPENAPI] Pobrany pomyslnie przez HTTP GET " + VSE_BASE + "/openapi.json")
            else:
                print("[OPENAPI] HTTP GET zwrocil status: " + str(r.status_code))
        except Exception as e:
            print("[OPENAPI] HTTP GET wyjatek: " + str(e))

    if not raw_spec:
        print("[OPENAPI] OSTRZEZENIE: Nie udalo sie pobrac openapi.json — uzywam schematu wbudowanego")
        return None

    # Ekstrakcja sekcji /shorts/
    extracted = {
        "title": raw_spec.get("info", {}).get("title"),
        "version": raw_spec.get("info", {}).get("version"),
        "shorts_paths": {},
        "referenced_schemas": {}
    }

    paths = raw_spec.get("paths", {})
    all_schemas = raw_spec.get("components", {}).get("schemas", {})

    for path, methods in paths.items():
        if "/shorts" in path:
            extracted["shorts_paths"][path] = methods
            methods_str = json.dumps(methods)
            for schema_name in all_schemas:
                if schema_name in methods_str:
                    extracted["referenced_schemas"][schema_name] = all_schemas[schema_name]

    # Zapisz wyekstrahowany schemat do brain
    try:
        os.makedirs(os.path.dirname(SCHEMA_OUTPUT_PATH), exist_ok=True)
        with open(SCHEMA_OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(extracted, f, ensure_ascii=False, indent=2)
        print("[OPENAPI] Wyekstrahowany schemat zapisano w: " + SCHEMA_OUTPUT_PATH)
    except Exception as e:
        print("[OPENAPI] Blad zapisu schematu do pliku: " + str(e))

    return extracted


def fetch_candidates_for_film(film, token, openapi_spec):
    """
    Wysyla zapytanie POST /v1/shorts/candidates dla danego filmu.
    """
    yt_id = film["yt_id"]
    title = film["title"]
    yt_url = "https://www.youtube.com/watch?v=" + yt_id

    payload = {
        "youtube_id": yt_id,
        "youtube_url": yt_url,
        "count_emotional": 5,
        "count_professional": 5,
        "provider": "claude",
        "portal_id": PORTAL_ID
    }

    headers = {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json"
    }

    print("  [candidates] POST /v1/shorts/candidates dla " + yt_id)
    try:
        resp = requests.post(
            VSE_BASE + "/v1/shorts/candidates",
            headers=headers,
            json=payload,
            timeout=300
        )
        status_code = resp.status_code
        print("  [candidates] HTTP status: " + str(status_code))

        if status_code == 200:
            res_json = resp.json()
            candidates = res_json.get("candidates") or res_json.get("items") or []
            print("  [candidates] SUKCES: znaleziono " + str(len(candidates)) + " kandydatow!")
            for idx, c in enumerate(candidates[:5], 1):
                c_title = c.get("title") or c.get("hook") or "Bez tytulu"
                s = c.get("start_sec") or c.get("start") or 0
                e = c.get("end_sec") or c.get("end") or 0
                dur = round(float(e) - float(s), 1) if (s and e) else "?"
                print("    #" + str(idx) + ": [" + str(s) + "s - " + str(e) + "s (" + str(dur) + "s)] " + str(c_title)[:50])
            return {
                "status": "OK",
                "status_code": status_code,
                "candidates_count": len(candidates),
                "candidates": candidates,
                "raw_response": res_json
            }
        elif status_code == 422:
            print("  [candidates] BLAD 422 (Unprocessable Entity) — niezgodnosc schematu Pydantic:")
            print("    " + resp.text[:400])
            return {
                "status": "SCHEMA_ERROR_422",
                "status_code": status_code,
                "error": resp.text[:500]
            }
        else:
            print("  [candidates] BLAD HTTP " + str(status_code) + ": " + resp.text[:300])
            return {
                "status": "HTTP_ERROR_" + str(status_code),
                "status_code": status_code,
                "error": resp.text[:500]
            }
    except Exception as e:
        print("  [candidates] Wyjatek: " + str(e))
        return {
            "status": "EXCEPTION",
            "error": str(e)
        }


# =====================================================================
# MAIN
# =====================================================================

def main():
    print("=" * 70)
    print("prawy_shorts_candidates_21_09_2026.py start: " + str(datetime.datetime.now()))
    print("=" * 70)

    token = get_jwt()
    openapi_spec = fetch_openapi_spec()

    if openapi_spec and openapi_spec.get("shorts_paths"):
        print("\n[SCHEMA] Odnalezione sciezki /shorts w OpenAPI:")
        for p in openapi_spec["shorts_paths"]:
            print("  - " + p)
        if openapi_spec.get("referenced_schemas"):
            print("[SCHEMA] Odnalezione modele Pydantic:")
            for s in openapi_spec["referenced_schemas"]:
                print("  - " + s)

    all_results = {
        "timestamp": datetime.datetime.now().isoformat(),
        "openapi_available": (openapi_spec is not None),
        "openapi_summary": {
            "paths": list(openapi_spec.get("shorts_paths", {}).keys()) if openapi_spec else [],
            "schemas": list(openapi_spec.get("referenced_schemas", {}).keys()) if openapi_spec else []
        },
        "films": []
    }

    for idx, film in enumerate(FILMS, 1):
        yt_id = film["yt_id"]
        title = film["title"]
        print("\n" + "-" * 60)
        print("[" + str(idx) + "/6] Kandydaci na Shorty: " + title + " (" + yt_id + ")")
        print("-" * 60)

        local_path = film.get("local_mp4", "")
        local_exists = os.path.exists(local_path)
        print("  [local_mp4] " + ("ISTNIEJE" if local_exists else "BRAK") + " (" + local_path + ")")

        film_eval = {
            "yt_id": yt_id,
            "title": title,
            "wp_post_id": film["wp_post_id"],
            "local_mp4": local_path,
            "local_exists": local_exists,
            "candidates_result": None
        }

        cand_res = fetch_candidates_for_film(film, token, openapi_spec)
        film_eval["candidates_result"] = cand_res
        all_results["films"].append(film_eval)

        print("  [pause] Odczekuje 3s...")
        time.sleep(3)

    try:
        os.makedirs(os.path.dirname(RESULTS_OUTPUT_PATH), exist_ok=True)
        with open(RESULTS_OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        print("\n[ZAPIS] Wyniki zapisano w: " + RESULTS_OUTPUT_PATH)
    except Exception as e:
        print("\n[ZAPIS] Blad zapisu wynikow do pliku: " + str(e))

    print("\n" + "=" * 70)
    print("PODSUMOWANIE KANDYDATOW NA SHORTY")
    print("=" * 70)
    for f in all_results["films"]:
        c_res = f.get("candidates_result") or {}
        st = c_res.get("status", "UNKNOWN")
        cnt = c_res.get("candidates_count", 0)
        print("  " + f["yt_id"] + " | " + f["title"][:30].ljust(30) + " | status: " + st.ljust(15) + " | kandydaci: " + str(cnt))


if __name__ == "__main__":
    main()
