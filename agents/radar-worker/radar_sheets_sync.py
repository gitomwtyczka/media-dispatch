#!/usr/bin/env python3
import gspread
import json, time, subprocess, requests, os, sys, re
from pathlib import Path
from datetime import datetime

# ===== CONFIG =====
PRESSAI_URL = "https://press.impresjapr.pl"
RADAR_URL   = "https://radar.impresjapr.pl"
SHEET_ID    = "1zqwvS784EaZh1EJIcXk1DliAau1r4X15ENFJjloDSaM"
TAB_NAME    = "Propozycje Radar"
SERVICE_ACC = os.environ.get("GOOGLE_SA_KEY_PATH", "/home/ubuntu/otwock-data/muzeum/muzeum-drive-sa.json")
SSH_KEY     = r"C:\Users\tomas2\.ssh\oracle-crimson.key"
VPS         = "ubuntu@147.224.162.100"
PORTAL_ID   = "2b047d7d-15a1-4d2f-8463-f89c2275bb73" # domyślnie prawy.pl

def get_pressai_jwt():
    token = os.environ.get('PRESSAI_JWT_USER')
    if not token:
        raise RuntimeError("Brak tokenu PRESSAI_JWT_USER w .env")
    return token

def get_radar_jwt():
    token = os.environ.get('CONTENT_RADAR_JWT')
    if not token:
        raise RuntimeError("Brak tokenu CONTENT_RADAR_JWT w .env")
    return token

def auth_header(token): 
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

def ensure_sheet(gc, sh):
    try:
        ws = sh.worksheet(TAB_NAME)
    except gspread.exceptions.WorksheetNotFound:
        print(f"Tworzę nową zakładkę '{TAB_NAME}'")
        ws = sh.add_worksheet(title=TAB_NAME, rows="100", cols="8")
        ws.update('A1:H1', [["Temat", "Źródło", "Link do źródła", "Data opublikowania źródła", "Tytuł SEO", "Frazy kluczowe", "Obrazek główny", "Status"]])
    return ws

def mode_fetch(ws):
    print("--- TRYB FETCH: Pobieranie trendów z Content Radar ---")
    try:
        token = get_radar_jwt()
    except Exception as e:
        print(f"Nie można pobrać tokenu cr-api ({e}). Pomijam pobieranie z Radaru.")
        return
        
    if not token:
        print("Brak JWT z cr-api, pomijam fetch.")
        return
        
    try:
        resp = requests.get(f"{RADAR_URL}/api/v1/trending/global", headers=auth_header(token), params={"limit": 10}, timeout=15)
        if resp.status_code != 200:
            print(f"Błąd Radaru: {resp.status_code}")
            return
            
        posts = resp.json()
        if not posts:
            print("Brak trendów.")
            return
            
        existing_urls = [row[2] for row in ws.get_all_values()[1:] if len(row) > 2]
        
        new_rows = []
        for p in posts:
            url = p.get('url', '')
            if url and url not in existing_urls:
                title = p.get('title') or p.get('summary', '')
                new_rows.append([
                    title,
                    "",
                    url,
                    "",
                    "",
                    "",
                    "",
                    "Nowa Propozycja"
                ])
                existing_urls.append(url)
                
        if new_rows:
            ws.append_rows(new_rows)
            print(f"Dodano {len(new_rows)} propozycji do zakładki '{TAB_NAME}'.")
        else:
            print("Brak nowych trendów.")
    except Exception as e:
        print(f"Błąd podczas pobierania trendów: {e}")

def process_row_publish(row, row_idx, ws, pressai_token):
    # 8 kolumn: 0:Temat, 1:Źródło, 2:Link, 3:Data, 4:Tytuł SEO, 5:Frazy, 6:Obrazek, 7:Status
    while len(row) < 8:
        row.append("")
        
    status = row[7].strip()
    if status != "Publikuj w PressAI":
        return
        
    temat = row[0].strip()
    url = row[2].strip()
    tytul_seo = row[4].strip()
    frazy = row[5].strip()
    obrazek = row[6].strip()
    
    if not tytul_seo:
        tytul_seo = temat
    
    print(f"\nProcessing row {row_idx+1}: {tytul_seo}")
    
    # KROK 1: Extract
    source_text = url
    if url.startswith("http"):
        print("  [1] Extracting URL...")
        r_ext = requests.post(f"{PRESSAI_URL}/api/editor/extract", headers=auth_header(pressai_token), json={"url": url}, timeout=30)
        if r_ext.status_code == 200:
            source_text = r_ext.json().get("text") or r_ext.json().get("content") or url
            
    if not source_text:
        print("  [BŁĄD] Brak source_text — pomijam wiersz.")
        return

    # KROK 2: Generate w PressAI
    print("  [2] Generowanie artykułu...")
    payload = {
        "source_text": source_text,
        "target_portal": PORTAL_ID,
        "selected_phrase": frazy,
        "seo_context": "",
        "model_provider": "anthropic",
        "model_name": "claude-sonnet-4-6",
        "formats": ["analiza", "feature"],
        "generate_faq": True,
        "custom_instructions": (
            "Artykuł musi mieć minimum 600 słów (optymalnie 800-1000 słów). "
            "Tytuł SEO: chwytliwy, dziennikarski, z główną frazą kluczową w H1. "
            "Język: polski, styl redakcyjny wysokiej jakości, zgodny z zasadami Google Discover. "
            "Wzbogac o kontekst branżowy i powiązania rynkowe. "
            "Sekcja FAQ na końcu: minimum 3 pytania i odpowiedzi. "
            "Formatuj w czystym HTML z nagłówkami H2, H3, akapitami i listami."
        ),
        "is_in_extenso": False,
        "image_metadata": []
    }
    
    if obrazek:
        payload["image_metadata"] = [{"path": obrazek}]
        
    r_gen = requests.post(f"{PRESSAI_URL}/api/editor/generate", headers=auth_header(pressai_token), json=payload, timeout=300)
    
    if r_gen.status_code != 200:
        print(f"  [BŁĄD] Generacja nie powiodła się: {r_gen.text[:200]}")
        return
        
    # Parsowanie odpowiedzi SSE z generatora
    generated_text = ""
    for line in r_gen.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith("data: "):
                try:
                    data = json.loads(line_str[6:])
                    text = data.get('result', {}).get('generated_article', '')
                    if text:
                        generated_text = text
                except Exception:
                    pass
                
    if not generated_text:
        print("  [BŁĄD] Pusty wynik z generatora.")
        return
        
    # KROK 3: Zapis do historii (Szkic w PressAI)
    print("  [3] Zapisywanie do historii PressAI...")
    r_save = requests.post(f"{PRESSAI_URL}/api/articles/", headers=auth_header(pressai_token), json={
        "portal": PORTAL_ID,
        "content": generated_text,
        "title": tytul_seo,
        "status": "draft"
    }, timeout=30)
    
    if r_save.status_code not in (200, 201):
        print(f"  [BŁĄD] Zapis historii: {r_save.text[:200]}")
        return
        
    saved = r_save.json()
    article_id = saved.get("id")
    print(f"  [OK] Zapisano artykuł PressAI ID: {article_id}")
    
    # KROK 4: Publikacja (zapis do WP) - jako Draft
    print("  [4] Przesyłanie do WP (Draft)...")
    r_pub = requests.post(f"{PRESSAI_URL}/api/publisher/publish", headers=auth_header(pressai_token), json={
        "article_id": str(article_id),
        "portal_id": PORTAL_ID,
        "publish_date": datetime.now().isoformat(),
        "status": "draft"
    }, timeout=60)
    
    wp_post_id = None
    if r_pub.status_code == 200:
        wp_post_id = r_pub.json().get("wp_post_id") or r_pub.json().get("id")
        print(f"  [OK] Zapisano jako Draft w WP (Post ID: {wp_post_id})")
    
    # KROK 5: Upload obrazka bezpośrednio do WP
    if obrazek and wp_post_id:
        print(f"  [5] Upload obrazka do WP: {obrazek}")
        upload_wp_image(obrazek, wp_post_id)
        
    # KROK 6: Aktualizacja excela
    try:
        ws.update_cell(row_idx + 1, 8, "Opublikowane")
    except Exception as e:
        print(f"  [BŁĄD] Aktualizacja arkusza: {e}")

def upload_wp_image(image_path: str, post_id):
    path = Path(image_path.strip('"\' '))
    if not path.exists():
        print(f"  [IMG] ERROR: Plik obrazka nie istnieje: {path}")
        return
        
    remote_tmp = f"/tmp/upload_{int(time.time())}_{path.name}"
    subprocess.run(["scp", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no", str(path), f"{VPS}:{remote_tmp}"], check=True)
    
    code = (
        "import asyncio, requests\n"
        "from api.db import AsyncSessionLocal\n"
        "from api.models.portal import WpPortal\n"
        "from core.injector import _make_auth\n"
        "import uuid, os\n"
        "async def main():\n"
        "    async with AsyncSessionLocal() as db:\n"
        f"        portal = await db.get(WpPortal, uuid.UUID('{PORTAL_ID}'))\n"
        "        auth = _make_auth(portal.wp_username, portal.wp_app_password)\n"
        "        wp_url = portal.url.rstrip('/')\n"
        f"        filepath = '{remote_tmp}'\n"
        "        filename = os.path.basename(filepath)\n"
        "        with open(filepath, 'rb') as f: data = f.read()\n"
        "        headers = {'Content-Disposition': f'attachment; filename=\"{filename}\"', 'Content-Type': 'image/jpeg'}\n"
        f"        res = requests.post(f'{wp_url}/wp-json/wp/v2/media', auth=auth, headers=headers, data=data)\n"
        "        if res.status_code in (200, 201):\n"
        "            media_id = res.json().get('id')\n"
        f"            res2 = requests.post(f'{wp_url}/wp-json/wp/v2/posts/{post_id}', json={{'featured_media': media_id}}, auth=auth)\n"
        "            print(f'MEDIA_OK: {media_id}')\n"
        "        else:\n"
        "            print(f'FAIL_MEDIA: {res.status_code} {res.text[:100]}')\n"
        "asyncio.run(main())\n"
    )
    cmd_ssh = ["ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no", VPS, f"docker exec -w /app vse-api python3 -c {subprocess.list2cmdline([code])}"]
    r = subprocess.run(cmd_ssh, capture_output=True, text=True, encoding="utf-8")
    print(f"  [IMG] {r.stdout.strip()}")

def main():
    print("Start: radar_sheets_sync.py")
    gc = gspread.service_account(filename=SERVICE_ACC)
    sh = gc.open_by_key(SHEET_ID)
    ws = ensure_sheet(gc, sh)
    
    # Tryb 1: Fetch
    mode_fetch(ws)
    
    # Tryb 2: Publish
    print("\n--- TRYB PUBLISH: Szukanie zadań w zakładce ---")
    rows = ws.get_all_values()
    if len(rows) > 1:
        pressai_token = get_pressai_jwt()
        for row_idx, row in enumerate(rows[1:], start=1):
            process_row_publish(row, row_idx, ws, pressai_token)
    else:
        print("Arkusz jest pusty (tylko nagłówki).")

if __name__ == "__main__":
    main()
