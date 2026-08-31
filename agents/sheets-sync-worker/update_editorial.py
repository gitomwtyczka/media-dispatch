#!/usr/bin/env python3
"""
Sheets Sync Worker — Aktualizacja Google Sheets Harmonogram Editorial
Arkusz: https://docs.google.com/spreadsheets/d/1zqwvS784EaZh1EJIcXk1DliAau1r4X15ENFJjloDSaM/edit?gid=809929940
Sheet ID: 1zqwvS784EaZh1EJIcXk1DliAau1r4X15ENFJjloDSaM
GID: 809929940

Uruchomienie:
  python update_editorial.py --service-account path/to/credentials.json
  python update_editorial.py --oauth
  python update_editorial.py --dry-run
  python update_editorial.py --export-csv editorial_update.csv
"""

import argparse
import csv
import io
import os
import sys
from typing import Any, Dict, List, Optional

DEFAULT_SHEET_ID = "1zqwvS784EaZh1EJIcXk1DliAau1r4X15ENFJjloDSaM"
DEFAULT_GID = 809929940

HEADERS = [
    "Lp",
    "YouTube ID",
    "Tytuł",
    "Krótki opis",
    "Czas trwania",
    "YT URL",
    "WP Draft URL",
    "Data emisji",
    "Godzina emisji",
    "Status",
    "Notatki",
    "Shorty",
    "Short Machine",
    "Tytuł SEO",
    "Frazy kluczowe",
]

NEW_ROWS: List[Dict[str, Any]] = [
    {
        "Lp": 10,
        "YouTube ID": "s6aGNXdtKpA",
        "Tytuł": "Mosiński: Porozumienia sierpniowe 1980 i narodziny Solidarności",
        "Krótki opis": "Jan Mosiński o kulisach porozumień sierpniowych 1980 roku i narodzinach NSZZ Solidarność.",
        "Czas trwania": "38:46",
        "YT URL": "https://www.youtube.com/watch?v=s6aGNXdtKpA",
        "WP Draft URL": "https://prawy.pl/porozumienia-sierpniowe-1980-jan-mosinski-o-narodzinach-solidarnosci/",
        "Data emisji": "31.08.2026",
        "Godzina emisji": "(brak)",
        "Status": "opublikowany",
        "Notatki": "WP #125353, live",
        "Shorty": "5",
        "Short Machine": "TAK",
        "Tytuł SEO": "Porozumienia sierpniowe 1980: Mosiński o Solidarności",
        "Frazy kluczowe": "porozumienia sierpniowe 1980, Solidarność, Jan Mosiński",
    },
    {
        "Lp": 11,
        "YouTube ID": "zYcq-57Y0ts",
        "Tytuł": "Mosiński: Testament Solidarności — co zostało z idei roku 80?",
        "Krótki opis": "Mosiński o tym co pozostało z idei Solidarności po 44 latach.",
        "Czas trwania": "-",
        "YT URL": "https://www.youtube.com/watch?v=zYcq-57Y0ts",
        "WP Draft URL": "https://prawy.pl/?p=125367",
        "Data emisji": "(czeka)",
        "Godzina emisji": "(czeka)",
        "Status": "wstrzymany",
        "Notatki": "User wycofał 2x — czeka na dyspozycję",
        "Shorty": "5",
        "Short Machine": "TAK",
        "Tytuł SEO": "Testament Solidarności: Co zostało z idei roku 80?",
        "Frazy kluczowe": "testament Solidarności, Jan Mosiński, idee Solidarności",
    },
    {
        "Lp": 12,
        "YouTube ID": "EnclbKLEDAA",
        "Tytuł": "Rulewski vs Michałowski: Kłótnia o Solidarność i jej spadek",
        "Krótki opis": "Jan Rulewski i Bogdan Michałowski o sporze dotyczącym dziedzictwa NSZZ Solidarność.",
        "Czas trwania": "-",
        "YT URL": "https://www.youtube.com/watch?v=EnclbKLEDAA",
        "WP Draft URL": "https://prawy.pl/?p=125372",
        "Data emisji": "(czeka)",
        "Godzina emisji": "(czeka)",
        "Status": "draft",
        "Notatki": "WP draft, YT unlisted — czeka na datę",
        "Shorty": "5",
        "Short Machine": "W TOKU",
        "Tytuł SEO": "Rulewski vs Michałowski: Spór o spadek Solidarności",
        "Frazy kluczowe": "Jan Rulewski, Bogdan Michałowski, historia Solidarności",
    },
    {
        "Lp": 13,
        "YouTube ID": "cDMAe_wx_AU",
        "Tytuł": "Helena Wolińska: bestia w mundurze i morderca gen. Nila",
        "Krótki opis": "Tadeusz Płużański ujawnia kulisy ekstradycji Heleny Wolińskiej i wybielania stalinowskiej zbrodniarki.",
        "Czas trwania": "53:08",
        "YT URL": "https://www.youtube.com/watch?v=cDMAe_wx_AU",
        "WP Draft URL": "(w toku)",
        "Data emisji": "01.09.2026",
        "Godzina emisji": "(brak)",
        "Status": "publikacja w toku",
        "Notatki": "Klimczak Płużański Wolińska, render shortów w toku",
        "Shorty": "5 (render)",
        "Short Machine": "W TOKU",
        "Tytuł SEO": "Helena Wolińska: Bestia w mundurze i morderca gen. Nila",
        "Frazy kluczowe": "Helena Wolińska, Tadeusz Płużański, gen Fieldorf Nil",
    },
    {
        "Lp": 14,
        "YouTube ID": "yQ-Q_YrleLE",
        "Tytuł": "Klimczak Śliwka Nowacka",
        "Krótki opis": "[VSE w toku — brak opisu]",
        "Czas trwania": "15:18",
        "YT URL": "https://www.youtube.com/watch?v=yQ-Q_YrleLE",
        "WP Draft URL": "(w toku)",
        "Data emisji": "(hold)",
        "Godzina emisji": "(hold)",
        "Status": "hold",
        "Notatki": "User powiedział hold. VSE done, wp_id=0.",
        "Shorty": "0",
        "Short Machine": "NIE",
        "Tytuł SEO": "Klimczak, Śliwka, Nowacka: Komentarz polityczny",
        "Frazy kluczowe": "Klimczak, Śliwka, Barbara Nowacka",
    },
]


def row_dict_to_list(row: Dict[str, Any], headers: List[str]) -> List[Any]:
    return [row.get(h, "") for h in headers]


def export_csv(filepath: str, delimiter: str = ",") -> None:
    with open(filepath, mode="w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=delimiter)
        writer.writerow(HEADERS)
        for row in NEW_ROWS:
            writer.writerow(row_dict_to_list(row, HEADERS))
    print(f"[OK] Zapisano ({len(NEW_ROWS)} wierszy) do: {filepath}")


def get_gspread_client(sa_path: Optional[str] = None, use_oauth: bool = False):
    try:
        import gspread
    except ImportError:
        print("[ERROR] Biblioteka 'gspread' nie jest zainstalowana. Zainstaluj: pip install gspread google-auth")
        sys.exit(1)

    if sa_path and os.path.exists(sa_path):
        print(f"[INFO] Autoryzacja Service Account z pliku: {sa_path}")
        return gspread.service_account(filename=sa_path)

    env_sa = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if env_sa and os.path.exists(env_sa):
        print(f"[INFO] Autoryzacja Service Account z GOOGLE_APPLICATION_CREDENTIALS: {env_sa}")
        return gspread.service_account(filename=env_sa)

    for default_name in ["service_account.json", "credentials.json", "sa.json"]:
        if os.path.exists(default_name):
            print(f"[INFO] Znaleziono lokalny plik credentials: {default_name}")
            return gspread.service_account(filename=default_name)

    if use_oauth:
        print("[INFO] Autoryzacja przez OAuth przeglądarkowy (gspread.oauth)...")
        return gspread.oauth()

    print("[ERROR] Nie znaleziono pliku credentials ani nie podano flagi --oauth / --service-account.")
    print("        Wskazówka: podaj ścieżkę do klucza: python update_editorial.py --service-account /sciezka/sa.json")
    print("        lub użyj logowania OAuth: python update_editorial.py --oauth")
    sys.exit(1)


def update_sheet(sheet_id: str, gid: int, client: Any) -> None:
    print(f"[INFO] Otwieranie arkusza: {sheet_id}...")
    spreadsheet = client.open_by_key(sheet_id)

    worksheet = None
    for ws in spreadsheet.worksheets():
        if ws.id == gid:
            worksheet = ws
            break
    if not worksheet:
        print(f"[WARN] Nie znaleziono zakładki o GID {gid}. Używam pierwszej zakładki: '{spreadsheet.sheet1.title}'")
        worksheet = spreadsheet.sheet1
    else:
        print(f"[INFO] Znaleziono zakładkę: '{worksheet.title}' (GID: {gid})")

    # Pobierz obecny stan nagłówków
    all_values = worksheet.get_all_values()
    if not all_values:
        print("[INFO] Arkusz pusty. Wstawianie pełnych nagłówków...")
        worksheet.append_row(HEADERS)
        current_headers = HEADERS
        existing_rows = []
    else:
        current_headers = all_values[0]
        existing_rows = all_values[1:]

    print(f"[INFO] Obecne nagłówki ({len(current_headers)} kolumn): {current_headers}")

    # Aktualizacja nagłówków jeśli brakuje nowych kolumn
    if len(current_headers) < len(HEADERS) or current_headers[:len(HEADERS)] != HEADERS:
        print(f"[INFO] Aktualizowanie nagłówków do {len(HEADERS)} kolumn...")
        worksheet.update("A1", [HEADERS])
        print("[OK] Zaktualizowano nagłówki.")

    # Mapa istniejących wierszy po Lp lub YouTube ID
    existing_map = {}
    for idx, row in enumerate(existing_rows, start=2):
        lp_val = str(row[0]).strip() if len(row) > 0 else ""
        yt_id_val = str(row[1]).strip() if len(row) > 1 else ""
        if lp_val:
            existing_map[lp_val] = idx
        if yt_id_val:
            existing_map[yt_id_val] = idx

    appended_count = 0
    updated_count = 0

    for item in NEW_ROWS:
        lp_key = str(item["Lp"])
        yt_key = str(item["YouTube ID"])
        row_vals = row_dict_to_list(item, HEADERS)

        target_row_idx = existing_map.get(lp_key) or existing_map.get(yt_key)
        if target_row_idx:
            print(f"[INFO] Aktualizowanie istniejącego wiersza #{target_row_idx} (Lp {lp_key}, {yt_key})...")
            worksheet.update(f"A{target_row_idx}", [row_vals])
            updated_count += 1
        else:
            print(f"[INFO] Dodawanie nowego wiersza (Lp {lp_key}, {yt_key})...")
            worksheet.append_row(row_vals)
            appended_count += 1

    print(f"[SUKCES] Zakończono aktualizację Google Sheets. Dodano: {appended_count}, Zaktualizowano: {updated_count}.")


def main():
    parser = argparse.ArgumentParser(description="Aktualizacja harmonogramu editorial w Google Sheets.")
    parser.add_argument("--sheet-id", default=DEFAULT_SHEET_ID, help="ID arkusza Google Sheets")
    parser.add_argument("--gid", type=int, default=DEFAULT_GID, help="GID zakładki")
    parser.add_argument("--service-account", "-s", help="Ścieżka do pliku JSON konta usługi (Service Account)")
    parser.add_argument("--oauth", action="store_true", help="Użyj autoryzacji OAuth2 przez przeglądarkę")
    parser.add_argument("--export-csv", help="Eksportuj nowe wiersze do pliku CSV")
    parser.add_argument("--export-tsv", help="Eksportuj nowe wiersze do pliku TSV (wklejanie Tab-separated)")
    parser.add_argument("--dry-run", action="store_true", help="Pokaż wiersze bez wysyłania do Google Sheets")

    args = parser.parse_args()

    if args.export_csv:
        export_csv(args.export_csv, delimiter=",")

    if args.export_tsv:
        export_csv(args.export_tsv, delimiter="\t")

    if args.dry_run:
        print("[DRY-RUN] Nagłówki:")
        print(" | ".join(HEADERS))
        print("-" * 100)
        for r in NEW_ROWS:
            print(" | ".join(str(x) for x in row_dict_to_list(r, HEADERS)))
        return

    if not args.export_csv and not args.export_tsv:
        client = get_gspread_client(sa_path=args.service_account, use_oauth=args.oauth)
        update_sheet(sheet_id=args.sheet_id, gid=args.gid, client=client)


if __name__ == "__main__":
    main()
