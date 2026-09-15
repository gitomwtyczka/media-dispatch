import subprocess, json, requests, sys

SSH_KEY = r"C:\Users\tomas2\.ssh\oracle-crimson.key"
VPS = "ubuntu@147.224.162.100"
VSE_BASE = "https://vse.impresjapr.pl"
PORTAL_ID = "2b047d7d-15a1-4d2f-8463-f89c2275bb73"
USER_ID = "4b97ab0c-98ee-46c6-9be8-d86adc4cb38a"

def get_jwt():
    code = (
        "import os, datetime; from jose import jwt; "
        "s=os.environ.get('JWT_SECRET_KEY',''); "
        "p={'sub':'4b97ab0c-98ee-46c6-9be8-d86adc4cb38a','exp':datetime.datetime.utcnow()+datetime.timedelta(hours=24)}; "
        "print(jwt.encode(p,s,algorithm='HS256'))"
    )
    cmd = ["ssh","-i",SSH_KEY,"-o","StrictHostKeyChecking=no",VPS,
           f'docker exec vse-api python3 -c "{code}"']
    r = subprocess.run(cmd, capture_output=True, timeout=30)
    token = r.stdout.decode('utf-8', errors='replace').strip()
    if not token: raise RuntimeError(f"JWT failed: {r.stderr.decode('utf-8','replace')[:200]}")
    return token

def get_vse_channel_ids():
    """
    Pobiera UUIDs kanałów z bazy VSE (potrzebne do publish-description).
    Zwraca listę stringów UUID.
    """
    cmd = ["ssh","-i",SSH_KEY,"-o","StrictHostKeyChecking=no",VPS,
           "docker exec vse-postgres psql -U vse -d vse -c "
           "\"SELECT id FROM youtube_channels WHERE is_active=true;\""]
    r = subprocess.run(cmd, capture_output=True, timeout=30)
    out = r.stdout.decode('utf-8', errors='replace')
    lines = [l.strip() for l in out.split('\n') if l.strip() and '-' in l and '|' not in l and 'id' not in l.lower()]
    uuids = [l for l in lines if len(l) == 36]
    print(f"[channels] Found UUIDs: {uuids}")
    return uuids

def get_schema_from_db(video_id):
    """Pobiera schema_data z ostatniego joba dla video_id."""
    cmd = ["ssh","-i",SSH_KEY,"-o","StrictHostKeyChecking=no",VPS,
           f"docker exec vse-postgres psql -U vse -d vse -c "
           f"\"SELECT schema_data::text FROM jobs WHERE video_id='{video_id}' ORDER BY created_at DESC LIMIT 1;\""]
    r = subprocess.run(cmd, capture_output=True, timeout=30)
    out = r.stdout.decode('utf-8', errors='replace')
    # Wyciągnij JSON z outputu psql
    lines = [l.strip() for l in out.split('\n') if l.strip() and not l.startswith('-') and not l.startswith('(') and l != 'schema_data']
    for line in lines:
        if line.startswith('{'):
            try:
                return json.loads(line)
            except:
                pass
    print(f"[db] Could not parse schema_data for {video_id}")
    return None

def step_publish_description(video_id, schema_data, channel_ids, token, wp_article_url=None):
    """
    Używa /v1/youtube/publish-description — VSE składa pełny opis sam.
    NIE używaj videos.update() ręcznie.
    """
    payload = {
        "channel_ids": channel_ids,
        "video_id": video_id,
        "schema_data": schema_data,
    }
    if wp_article_url:
        payload["wp_article_url"] = wp_article_url
    
    print(f"[publish-desc] POST /v1/youtube/publish-description for {video_id}")
    r = requests.post(
        f"{VSE_BASE}/v1/youtube/publish-description",
        headers={"Authorization": f"Bearer {token}"},
        json=payload, timeout=120
    )
    print(f"[publish-desc] {r.status_code}: {r.text[:300]}")
    return r.status_code == 200

def step_generate_with_transcript_check(yt_url, token, title=None):
    """
    Wywołuje /v1/generate i SPRAWDZA transcript_available.
    Zwraca (schema_data, transcript_ok).
    Jeśli transcript_available==False — zwraca (partial_schema, False).
    """
    payload = {
        "video_url": yt_url,
        "publication_type": "full_analysis",
        "portal_id": PORTAL_ID,
        "lang": "pl",
        "llm_provider": "claude"
    }
    if title:
        payload["post_title"] = title
    
    r = requests.post(f"{VSE_BASE}/v1/generate",
                      headers={"Authorization": f"Bearer {token}"},
                      json=payload, timeout=360)
    print(f"[generate] {r.status_code}: {r.text[:200]}")
    
    if r.status_code != 200:
        return None, False
    
    resp = r.json()
    schema_data = resp.get("schema_data")
    
    # KRYTYCZNY CHECK: czy był transkrypt?
    transcript_ok = resp.get("transcript_available", True)  # domyślnie True dla starszych wersji
    if schema_data:
        transcript_ok = transcript_ok and schema_data.get("transcript_available", True)
    
    if not transcript_ok:
        print(f"[generate] ⚠️ BRAK TRANSKRYPTU dla {yt_url} — wynik jest hallucynacją!")
    else:
        print(f"[generate] ✅ Transkrypt dostępny")
    
    return schema_data, transcript_ok

def step_inject(schema, yt_url, token, wp_post_id=None):
    """
    Tworzy lub nadpisuje post w WP. Zawsze draft!
    Jeśli wp_post_id podany — uży pola update_post_id (jeśli VSE wspiera) lub po prostu twórz nowy.
    """
    payload = {
        "video_url": yt_url,
        "schema_data": schema,
        "portal_id": PORTAL_ID,
        "post_status": "draft"  # ZAWSZE draft!
    }
    r = requests.post(f"{VSE_BASE}/v1/inject",
                      headers={"Authorization": f"Bearer {token}"},
                      json=payload, timeout=120)
    print(f"[inject] {r.status_code}: {r.text[:300]}")
    if r.status_code != 200:
        return None
    resp = r.json()
    return resp.get("wp_post_id") or resp.get("post_id")

def main():
    import datetime
    print(f"=== prawy_full_flow_v2.py {datetime.datetime.now()} ===")
    
    token = get_jwt()
    channel_ids = get_vse_channel_ids()
    
    if not channel_ids:
        print("[FATAL] Brak channel_ids z VSE DB! Sprawdz bazę.")
        sys.exit(1)
    
    results = []
    
    # === FILM 1: Wółyń — tylko napraw YT opis (schema OK, artykuł OK) ===
    print("\n=== Wółyń: Redo YT description ===")
    wolyn_schema = get_schema_from_db("EWkRL1sEqQE")
    wolyn_yt_ok = False
    if wolyn_schema:
        wolyn_yt_ok = step_publish_description(
            "EWkRL1sEqQE", wolyn_schema, channel_ids, token,
            wp_article_url="https://prawy.pl/?p=126276"
        )
        print(f"[Wółyń] YT description: {'OK' if wolyn_yt_ok else 'FAILED'}")
    else:
        print("[Wółyń] Brak schema_data w DB!")
    results.append({"film": "Wółyń", "yt_id": "EWkRL1sEqQE", "wp_post_id": 126276,
                    "yt_desc_updated": wolyn_yt_ok, "status": "desc_fixed"})
    
    # === FILM 2: Pietrzak — sprawdz transkrypt, jeśli OK generuj od nowa ===
    print("\n=== Pietrzak: Transcript check + regenerate ===")
    yt_url_pietrzak = "https://www.youtube.com/watch?v=s6qif3Ed57E"
    
    schema_pietrzak, transcript_ok = step_generate_with_transcript_check(
        yt_url_pietrzak, token, "Płużański Pietrzak"
    )
    
    if not transcript_ok:
        print("""
⚠️⚠️⚠️ BRAK TRANSKRYPTU DLA PIETRZAK (s6qif3Ed57E) ⚠️⚠️⚠️
YouTube nie udostępnił jeszcze napisów dla tego materiału.
Artykuł WP #126281 POZOSTAJE JAKO DRAFT — nie publikuj!
SPRÓBUJ PONOWNIE ZA OK. 30 MINUT uruchamiając ten skrypt.
Post WP #126281 NIC nie robi— pozostaje badziewny draft.
""")
        results.append({"film": "Pietrzak", "yt_id": "s6qif3Ed57E",
                        "status": "WAIT_FOR_TRANSCRIPT",
                        "action": "Uruchom skrypt ponownie za 30 min"})
    else:
        # Transkrypt OK — inject nowy post + opis YT
        print("[Pietrzak] Transkrypt OK — generuję artykuł i opis YT...")
        new_wp_id = step_inject(schema_pietrzak, yt_url_pietrzak, token)
        pietrzak_yt_ok = False
        if new_wp_id and schema_pietrzak:
            pietrzak_yt_ok = step_publish_description(
                "s6qif3Ed57E", schema_pietrzak, channel_ids, token,
                wp_article_url=f"https://prawy.pl/?p={new_wp_id}"
            )
        results.append({
            "film": "Pietrzak", "yt_id": "s6qif3Ed57E",
            "wp_post_id": new_wp_id, "yt_desc_updated": pietrzak_yt_ok,
            "status": "OK" if new_wp_id else "PARTIAL"
        })
    
    # Zapisz wyniki
    import json as _j
    out_path = r"C:\Users\tomas2\.gemini\antigravity\brain\phase1_v2_results.json"
    with open(out_path, 'w', encoding='utf-8') as f:
        _j.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n=== WYNIKI zapisane: {out_path} ===")
    print(_j.dumps(results, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()