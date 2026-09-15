import os
import json
import subprocess
import requests
import time
import glob
import datetime

FILMS = [
    {
        "yt_id": "EWkRL1sEqQE",
        "title": "Płużański Popek Wołyń 1",
        "local_mp4": r"C:\Users\tomas2\Videos\Prawy\Płużański Popek Wołyń 1.mp4"
    },
    {
        "yt_id": "s6qif3Ed57E",
        "title": "Płużański Pietrzak",
        "local_mp4": r"C:\Users\tomas2\Videos\Prawy\Płużański Pietrzak.mp4"
    },
]

SSH_KEY = r"C:\Users\tomas2\.ssh\oracle-crimson.key"
VPS = "ubuntu@147.224.162.100"
VSE_BASE = "https://vse.impresjapr.pl"
PORTAL_ID = "2b047d7d-15a1-4d2f-8463-f89c2275bb73"
LOCAL_OVERRIDES = r"C:\ProgramData\VSELocalRunner\local_overrides.json"
SHORTS_OUTPUT = r"C:\VSE\Shorts"

def update_local_overrides(films):
    """Dodaje/aktualizuje mapowanie YT ID -> lokalny MP4 w local_overrides.json"""
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

def get_jwt():
    code = (
        "import os, datetime; "
        "from jose import jwt; "
        "s = os.environ.get('JWT_SECRET_KEY', ''); "
        "p = {'sub': '4b97ab0c-98ee-46c6-9be8-d86adc4cb38a', 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)}; "
        "print(jwt.encode(p, s, algorithm='HS256'))"
    )
    cmd = ["ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no", VPS,
           f'docker exec vse-api python3 -c "{code}"']
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    token = r.stdout.strip()
    if not token:
        raise RuntimeError(f"JWT failed: {r.stderr[:200]}")
    print(f"[jwt] OK: {token[:20]}...")
    return token

def find_shorts_generate_endpoint(token):
    """Sprawdza openapi.json i zwraca endpoint do generowania shortów."""
    # Spróbuj pobrać przez SSH (unikamy escapingów)
    cmd = ["ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no", VPS,
           "curl -s http://localhost:8085/openapi.json"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    
    if r.returncode == 0 and r.stdout.strip():
        try:
            api_spec = json.loads(r.stdout)
            shorts_paths = [k for k in api_spec.get('paths', {}).keys() if 'short' in k.lower()]
            print(f"[api] Shorts endpoints found: {shorts_paths}")
            
            # Preferuj w tej kolejności:
            for candidate in ['/v1/shorts/generate', '/v1/shorts/create', '/v1/shorts/analyze', '/v1/shorts/candidates']:
                if candidate in shorts_paths:
                    return candidate
            
            # Fallback: pierwszy endpoint który nie jest describe/pending/result
            for path in shorts_paths:
                if not any(x in path for x in ['describe', 'pending', 'result', 'job']):
                    return path
        except:
            pass
    
    # Fallback: znany endpoint z runner.py
    print("[api] Could not parse openapi, using known endpoint /v1/shorts/generate")
    return "/v1/shorts/generate"

def generate_shorts_for_film(film, endpoint, token):
    """
    Wywołuje Short Machine API dla jednego filmu.
    Generuje 5 emotional + 5 professional.
    """
    url = f"{VSE_BASE}{endpoint}"
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
    print(f"[generate] POST {url}")
    r = requests.post(url, headers={"Authorization": f"Bearer {token}"}, json=payload, timeout=120)
    print(f"[generate] {r.status_code}: {r.text[:500]}")
    
    if r.status_code == 200:
        return r.json()
    elif r.status_code == 422:
        # Spróbuj bez niektórych pól
        payload_minimal = {
            "youtube_url": f"https://www.youtube.com/watch?v={film['yt_id']}",
            "portal_id": PORTAL_ID,
            "count_emotional": 5,
            "count_professional": 5,
        }
        r2 = requests.post(url, headers={"Authorization": f"Bearer {token}"}, json=payload_minimal, timeout=120)
        print(f"[generate-minimal] {r2.status_code}: {r2.text[:500]}")
        if r2.status_code == 200:
            return r2.json()
    return None

def wait_for_shorts(film_name, expected_count=10, max_wait=600):
    """Czeka aż Local Runner przetworzy joby i pliki pojawią się w C:\\VSE\\Shorts\\"""
    print(f"[wait] Waiting for {expected_count} shorts for '{film_name}'...")
    start = time.time()
    
    while time.time() - start < max_wait:
        pattern = os.path.join(SHORTS_OUTPUT, '**', '*.mp4')
        all_files = glob.glob(pattern, recursive=True)
        
        # Filtruj pliki pasujące do nazwy filmu
        film_slug = film_name[:20].replace(' ', '_').lower()
        matching = [f for f in all_files if any(
            part.lower().replace(' ', '_').startswith(film_slug[:10])
            for part in os.path.basename(f).lower().split('_')
        )]
        
        print(f"[wait] Found {len(all_files)} total MP4s in C:\\VSE\\Shorts, {len(matching)} matching '{film_name}'")
        
        if len(all_files) >= expected_count:
            return all_files
        
        time.sleep(15)
    
    # Zwróć co mamy
    return glob.glob(os.path.join(SHORTS_OUTPUT, '**', '*.mp4'), recursive=True)

def main():
    print("=" * 60)
    print(f"Prawy Short Machine Pipeline — {datetime.datetime.now()}")
    print(f"Films: {[f['title'] for f in FILMS]}")
    print("=" * 60)
    
    # 1. Aktualizuj local_overrides
    update_local_overrides(FILMS)
    
    # 2. JWT token
    token = get_jwt()
    
    # 3. Znajdź endpoint
    endpoint = find_shorts_generate_endpoint(token)
    print(f"[main] Using endpoint: {endpoint}")
    
    # 4. Generuj shorty per film
    results = []
    for film in FILMS:
        print(f"\n--- {film['title']} ---")
        resp = generate_shorts_for_film(film, endpoint, token)
        results.append({
            "film": film['title'],
            "yt_id": film['yt_id'],
            "generate_response": resp,
            "status": "queued" if resp else "FAILED"
        })
    
    # 5. Poczekaj na Local Runner (wszystkie filmy razem, maks 10 min)
    print("\n[main] Waiting for Local Runner to process jobs...")
    time.sleep(30)  # Daj runnerowi chwilę na start
    all_shorts = wait_for_shorts("all", expected_count=len(FILMS) * 10, max_wait=600)
    
    # 6. Zbierz wyniki
    print(f"\n[main] Shorts generated: {len(all_shorts)} files")
    for f in sorted(all_shorts):
        print(f"  {f}")
    
    # 7. Zapisz wyniki
    output = {
        "timestamp": str(datetime.datetime.now()),
        "films": results,
        "generated_files": all_shorts
    }
    results_path = r"C:\Users\tomas2\.gemini\antigravity\brain\phase2_results.json"
    with open(results_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n[main] Results saved to {results_path}")
    print(json.dumps(output, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()