#!/usr/bin/env python3
\"\"\"agents/sheets-sync-worker/apply_kandydaci_formatting.py

Aktualizuje reguły Conditional Formatting dla zakładki Kandydaci w arkuszu Google Sheets.
media-dispatch | media-dev-29 | 01.09.2026

Arkusz: 1HMuODAIOG8e_9VH-HitdL_TwBRwgFZ0vnSKAW7Wmyig
Zakładka: Kandydaci (GID: 1842692147)
Zakres: A2:R50

Reguły:
1. Gmail (złoty #FFD700): Kolumna C (Źródło) zawiera 'gmail:'
2. P0 (czerwony): Kolumna F (Priorytet) = 'P0'
3. P1 (pomarańczowy): Kolumna F = 'P1'
4. P2 (żółty): Kolumna F = 'P2'
5. P3 (szary): Kolumna F = 'P3'
\"\"\"

import argparse
import logging
import os
import sys
from typing import List, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
log = logging.getLogger('sheets-formatter')

DEFAULT_SPREADSHEET_ID = '1HMuODAIOG8e_9VH-HitdL_TwBRwgFZ0vnSKAW7Wmyig'
DEFAULT_GID = 1842692147


def get_credentials(sa_path: Optional[str] = None):
    try:
        from google.oauth2.service_account import Credentials
    except ImportError:
        log.error("Zainstaluj: pip3 install google-api-python-client google-auth gspread")
        sys.exit(1)

    candidates = [
        sa_path,
        os.environ.get('GOOGLE_SA_FILE'),
        '/home/ubuntu/otwock-data/muzeum/muzeum-drive-sa.json',
        'service_account.json',
        'credentials.json',
        'sa.json'
    ]

    for p in candidates:
        if p and os.path.exists(p):
            log.info("Używam pliku Service Account: %s", p)
            return Credentials.from_service_account_file(
                p,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )

    log.error("Nie znaleziono pliku Service Account. Podaj flagę --service-account /sciezka/sa.json")
    sys.exit(1)


def build_rules(sheet_id: int, start_row: int = 1, end_row: int = 50, start_col: int = 0, end_col: int = 18) -> List[dict]:
    grid_range = {
        'sheetId': sheet_id,
        'startRowIndex': start_row,
        'endRowIndex': end_row,
        'startColumnIndex': start_col,
        'endColumnIndex': end_col
    }

    rules_def = [
        {
            'name': 'Gmail Współpracownicy (złoty)',
            'formula': '=REGEXMATCH(LOWER($C2), "gmail:")',
            'color': {'red': 1.0, 'green': 0.843, 'blue': 0.0}  # #FFD700
        },
        {
            'name': 'P0 Priorytet (czerwony)',
            'formula': '=OR($F2="P0", REGEXMATCH(TO_TEXT($F2), "(?i)P0"))',
            'color': {'red': 0.957, 'green': 0.6, 'blue': 0.6}
        },
        {
            'name': 'P1 Priorytet (pomarańczowy)',
            'formula': '=OR($F2="P1", REGEXMATCH(TO_TEXT($F2), "(?i)P1"))',
            'color': {'red': 0.992, 'green': 0.749, 'blue': 0.502}
        },
        {
            'name': 'P2 Priorytet (żółty)',
            'formula': '=OR($F2="P2", REGEXMATCH(TO_TEXT($F2), "(?i)P2"))',
            'color': {'red': 1.0, 'green': 0.949, 'blue': 0.6}
        },
        {
            'name': 'P3 Priorytet (szary)',
            'formula': '=OR($F2="P3", REGEXMATCH(TO_TEXT($F2), "(?i)P3"))',
            'color': {'red': 0.85, 'green': 0.85, 'blue': 0.85}
        }
    ]

    requests = []
    for idx, r in enumerate(rules_def):
        req = {
            'addConditionalFormatRule': {
                'rule': {
                    'ranges': [grid_range],
                    'booleanRule': {
                        'condition': {
                            'type': 'CUSTOM_FORMULA',
                            'values': [{'userEnteredValue': r['formula']}]
                        },
                        'format': {
                            'backgroundColor': r['color']
                        }
                    }
                },
                'index': idx
            }
        }
        requests.append(req)

    return requests


def apply_formatting(spreadsheet_id: str, gid: int, sa_path: Optional[str] = None):
    try:
        from googleapiclient.discovery import build
    except ImportError:
        log.error("Zainstaluj google-api-python-client: pip3 install google-api-python-client")
        sys.exit(1)

    creds = get_credentials(sa_path)
    service = build('sheets', 'v4', credentials=creds)

    log.info("Pobieram metadane arkusza %s...", spreadsheet_id)
    sheet_metadata = service.spreadsheets().get(
        spreadsheetId=spreadsheet_id,
        fields='sheets(properties(sheetId,title),conditionalFormats)'
    ).execute()

    target_sheet = None
    for s in sheet_metadata.get('sheets', []):
        if s.get('properties', {}).get('sheetId') == gid:
            target_sheet = s
            break

    if not target_sheet:
        log.error("Nie znaleziono zakładki o GID %s", gid)
        sys.exit(1)

    existing_formats = target_sheet.get('conditionalFormats', [])
    log.info("Znaleziono %d istniejących reguł formatowania w '%s'", len(existing_formats), target_sheet['properties']['title'])

    batch_requests = []

    # 1. Usuń istniejące reguły w kolejności malejącej indeksów
    for i in reversed(range(len(existing_formats))):
        batch_requests.append({
            'deleteConditionalFormatRule': {
                'sheetId': gid,
                'index': i
            }
        })

    # 2. Dodaj nowe reguły
    new_rule_requests = build_rules(sheet_id=gid, start_row=1, end_row=50, start_col=0, end_col=18)
    batch_requests.extend(new_rule_requests)

    log.info("Wysyłam batchUpdate (%d operacji)...", len(batch_requests))
    body = {'requests': batch_requests}
    response = service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body=body
    ).execute()

    log.info("Sukces! Zaktualizowano reguły conditional formatting.")
    return response


def main():
    parser = argparse.ArgumentParser(description="Aktualizacja conditional formatting w Google Sheets.")
    parser.add_argument('--spreadsheet-id', default=DEFAULT_SPREADSHEET_ID, help="ID arkusza")
    parser.add_argument('--gid', type=int, default=DEFAULT_GID, help="GID zakładki (domyślnie 1842692147)")
    parser.add_argument('--service-account', '-s', help="Ścieżka do pliku service account JSON")

    args = parser.parse_args()
    apply_formatting(args.spreadsheet_id, args.gid, args.service_account)


if __name__ == '__main__':
    main()
