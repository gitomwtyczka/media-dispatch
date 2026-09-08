#!/usr/bin/env python3
"""agents/biznesciti-worker/biznesciti_sheets_sync.py

Publisher: czyta zakładkę 'Propozycje BiznesCiti' z Google Sheets,
generuje artykuły przez PressAI i publikuje jako draft w WP.
media-dispatch | arch-worker-01 | 08.09.2026
"""
import gspread
import json, time, requests, os, sys
from datetime import datetime

# ===== CONFIG =====
PRESSAI_URL = "https://press.impresjapr.pl"
SHEET_ID    = "1zqwvS784EaZh1EJIcXk1DliAau1r4X15ENFJjloDSaM"
TAB_NAME    = "Propozycje BiznesCiti"
SERVICE_ACC = os.environ.get("GOOGLE_SA_FILE", "/home/ubuntu/media-dispatch/config/service_account.json")
PORTAL_ID   = os.environ.get("BIZNESCITI_PORTAL_ID", "")  # UUID portalu biznesciti.com w PressAI
PORTAL_NAME = "BiznesCiti"

def get_pressai_jwt():
    token = os.environ.get('PRESSAI_JWT_USER')
    if not token:
        raise RuntimeError("Brak tokenu PRESSAI_JWT_USER w .env")
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

def process_row_publish(row, row_idx, ws, pressai_token):
    """Przetwarza jeden wiersz z arkusza.
    Kolumny: 0:Temat, 1:Źródło, 2:Link, 3:Data, 4:Tytuł SEO, 5:Frazy, 6:Obrazek, 7:Status
    """
    while len(row) < 8:
        row.append("")

    status = row[7].strip()
    if status != "Publikuj w PressAI":
        return

    temat = row[0].strip()
    url = row[2].strip()
    tytul_seo = row[4].strip() or temat
    frazy = row[5].strip()

    print(f"\nProcessing row {row_idx+1}: {tytul_seo}")

    # KROK 1: Extract
    source_text = url
    if url.startswith("http"):
        print("  [1] Extracting URL...")
        r_ext = requests.post(
            f"{PRESSAI_URL}/api/editor/extract",
            headers=auth_header(pressai_token),
            json={"url": url},
            timeout=30
        )
        if r_ext.status_code == 200:
            source_text = r_ext.json().get("content") or url

    if not source_text:
        print("  [BŁĄD] Brak source_text — pomijam wiersz.")
        return

    # KROK 2: Generate
    print("  [2] Generowanie artykułu...")
    target = PORTAL_ID if PORTAL_ID else PORTAL_NAME
    payload = {
        "source_text": source_text,
        "target_portal": target,
        "selected_phrase": frazy,
        "seo_context": "",
        "formats": ["analiza", "feature"],
        "generate_faq": True,
        "is_in_extenso": False,
        "image_metadata": []
    }

    r_gen = requests.post(
        f"{PRESSAI_URL}/api/editor/generate",
        headers=auth_header(pressai_token),
        json=payload,
        timeout=300
    )

    if r_gen.status_code != 200:
        print(f"  [BŁĄD] Generacja nie powiodła się: {r_gen.text[:200]}")
        return

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

    # KROK 3: Zapis do historii PressAI
    print("  [3] Zapisywanie do historii PressAI...")
    r_save = requests.post(
        f"{PRESSAI_URL}/api/articles/",
        headers=auth_header(pressai_token),
        json={
            "portal": target,
            "content": generated_text,
            "title": tytul_seo,
            "status": "draft"
        },
        timeout=30
    )

    if r_save.status_code not in (200, 201):
        print(f"  [BŁĄD] Zapis historii: {r_save.text[:200]}")
        return

    article_id = r_save.json().get("id")
    print(f"  [OK] Zapisano artykuł PressAI ID: {article_id}")

    # KROK 4: Publikacja WP Draft
    print("  [4] Przesyłanie do WP (Draft)...")
    r_pub = requests.post(
        f"{PRESSAI_URL}/api/publisher/publish",
        headers=auth_header(pressai_token),
        json={
            "article_id": str(article_id),
            "portal": target,
            "publish_date": datetime.now().isoformat(),
            "status": "draft"
        },
        timeout=60
    )

    if r_pub.status_code == 200:
        wp_post_id = r_pub.json().get("wp_post_id") or r_pub.json().get("id")
        print(f"  [OK] Zapisano jako Draft w WP (Post ID: {wp_post_id})")

    # KROK 5: Aktualizacja Sheets
    try:
        ws.update_cell(row_idx + 1, 8, "Opublikowane")
    except Exception as e:
        print(f"  [BŁĄD] Aktualizacja arkusza: {e}")

def main():
    print("Start: biznesciti_sheets_sync.py")
    gc = gspread.service_account(filename=SERVICE_ACC)
    sh = gc.open_by_key(SHEET_ID)
    ws = ensure_sheet(gc, sh)

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
