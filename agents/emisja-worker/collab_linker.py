"""agents/emisja-worker/collab_linker.py

Generator linków do współdzielenia wersji roboczych (draft-collab) dla WordPress (Prawy.pl)
zintegrowany z arkuszem Google Sheets "Emisja".

Architektura:
- Odczytuje arkusz Google Sheets (z uwzględnieniem hiperlinków i formuł HYPERLINK)
- Weryfikuje i dynamicznie tworzy kolumnę 'Link draft' jeśli nie istnieje
- Wyciąga identyfikator wpisu WordPress (post_id) z kolumny 'WP Draft URL' (?p=ID, post=ID lub slug)
- Generuje unikalny link kolaboracyjny przez WP REST API pluginu draft-collab
- Zapisuje wygenerowane linki wsadowo do arkusza Google Sheets

Wszystkie poświadczenia pobierane wyłącznie ze zmiennych środowiskowych.
"""

from __future__ import annotations

import logging
import os
import re
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests
from google.oauth2 import service_account
from googleapiclient.discovery import Resource, build

logger = logging.getLogger("emisja-worker.collab-linker")


def col_idx_to_letter(col_idx: int) -> str:
    """Konwertuje indeks kolumny 0-based na oznaczenie literowe A1 notation (0->A, 25->Z, 26->AA)."""
    result = ""
    col_idx += 1
    while col_idx > 0:
        col_idx, remainder = divmod(col_idx - 1, 26)
        result = chr(65 + remainder) + result
    return result


class CollabLinker:
    """Zarządza pobieraniem draftów z arkusza Sheets, generowaniem linków draft-collab w WordPress
    i aktualizacją arkusza.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Inicjalizacja CollabLinker.

        Args:
            config: Opcjonalny słownik konfiguracji nadpisujący zmienne środowiskowe.
                    Obsługiwane klucze:
                    - google_sa_file: ścieżka do pliku klucza Service Account
                    - sheets_emisja_id: ID arkusza Google Sheets
                    - wp_url: bazowy adres URL WordPress (np. https://prawy.pl)
                    - wp_user: nazwa użytkownika WordPress
                    - wp_pass: Application Password WordPress
                    - collab_email: domyślny email do autoryzacji linku
        """
        self.config = config or {}
        self.logger = logger

        # Konfiguracja środowiskowa (BEZ hardkodowanych sekretów!)
        self.sa_file = self.config.get("google_sa_file") or os.getenv("GOOGLE_SA_FILE")
        self.sheet_id = self.config.get("sheets_emisja_id") or os.getenv("SHEETS_EMISJA_ID")
        self.wp_url = (self.config.get("wp_url") or os.getenv("WP_URL", "https://prawy.pl")).rstrip("/")
        self.wp_user = self.config.get("wp_user") or os.getenv("WP_USER")
        self.wp_pass = self.config.get("wp_pass") or os.getenv("WP_PASS")
        self.collab_email = self.config.get("collab_email") or os.getenv("COLLAB_EMAIL", "tobroz@gmail.com")

        self._sheets_service: Optional[Resource] = None
        self._last_status: Dict[str, Any] = {
            "last_run": None,
            "status": "idle",
            "last_result": None,
            "error": None,
        }

    def _get_sheets_service(self) -> Resource:
        """Inicjalizuje i zwraca klienta Google Sheets API."""
        if self._sheets_service is not None:
            return self._sheets_service

        if not self.sa_file:
            raise ValueError(
                "Brak ścieżki do pliku klucza Service Account. "
                "Ustaw zmienną środowiskową GOOGLE_SA_FILE."
            )

        if not os.path.isfile(self.sa_file):
            raise FileNotFoundError(
                f"Plik Service Account nie istnieje pod ścieżką: {self.sa_file}"
            )

        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = service_account.Credentials.from_service_account_file(self.sa_file, scopes=scopes)
        self._sheets_service = build("sheets", "v4", credentials=creds, cache_discovery=False)
        return self._sheets_service

    def _extract_url_from_cell(self, cell: Dict[str, Any]) -> Optional[str]:
        """Wyciąga poprawny URL z komórki arkusza Google Sheets uwzględniając różne formaty."""
        if not cell:
            return None

        # 1. Sprawdź jawne właściwości hyperlink
        hyperlink = cell.get("hyperlink")
        if hyperlink and hyperlink.startswith("http"):
            return hyperlink.strip()

        # 2. Sprawdź formułę =HYPERLINK("url", "text")
        user_entered = cell.get("userEnteredValue", {})
        formula = user_entered.get("formulaValue", "")
        if formula and formula.strip().upper().startswith("=HYPERLINK"):
            match = re.search(r'=\s*HYPERLINK\s*\(\s*["\']([^"\']+)["\']', formula, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        # 3. Sprawdź formattedValue
        formatted = cell.get("formattedValue", "")
        if formatted and (formatted.startswith("http://") or formatted.startswith("https://")):
            return formatted.strip()

        # 4. Sprawdź stringValue
        string_val = user_entered.get("stringValue", "")
        if string_val and (string_val.startswith("http://") or string_val.startswith("https://")):
            return string_val.strip()

        # 5. Fallback regex w tekście
        candidates = [formatted, string_val]
        for text in candidates:
            if text:
                url_match = re.search(r'https?://[^\s"\'<>]+', text)
                if url_match:
                    return url_match.group(0).strip()

        return None

    def _extract_post_id_from_url(self, url: str) -> Optional[int]:
        """Wyodrębnia ID wpisu (post_id) z adresu URL.

        Obsługuje wzorce:
        - ?p=12345 lub &p=12345
        - ?post=12345 lub &post=12345
        - ?preview_id=12345
        - Odpytanie WP REST API po slugu w przypadku braku jawnego ID w query string.
        """
        if not url:
            return None

        parsed = urllib.parse.urlparse(url)
        qs = urllib.parse.parse_qs(parsed.query)

        # Sprawdź parametry query: post, p, preview_id
        for param in ("post", "p", "preview_id"):
            if param in qs and qs[param]:
                val = qs[param][0]
                if val.isdigit():
                    return int(val)

        # Regex fallback w całym URL
        regex_match = re.search(r'[?&](?:post|p|preview_id)=(\d+)', url)
        if regex_match:
            return int(regex_match.group(1))

        # Fallback: wyszukiwanie po slug w WP REST API
        path_segments = [seg for seg in parsed.path.strip("/").split("/") if seg and seg != "wp-admin"]
        if path_segments and self.wp_user and self.wp_pass:
            slug = path_segments[-1]
            if not slug.endswith(".php"):
                try:
                    api_endpoint = f"{self.wp_url}/wp-json/wp/v2/posts"
                    params = {
                        "slug": slug,
                        "status": "draft,pending,private,future,publish",
                    }
                    resp = requests.get(
                        api_endpoint,
                        params=params,
                        auth=(self.wp_user, self.wp_pass),
                        timeout=10,
                    )
                    if resp.status_code == 200:
                        posts = resp.json()
                        if isinstance(posts, list) and len(posts) > 0 and "id" in posts[0]:
                            return int(posts[0]["id"])
                except Exception as e:
                    self.logger.warning("Nieudane wyszukiwanie WP post_id po slug '%s': %s", slug, e)

        return None

    def _generate_collab_link(
        self,
        post_id: int,
        email: str,
        expire_on_publish: bool = False,
    ) -> Tuple[bool, str]:
        """Wywołuje endpoint wtyczki draft-collab w WordPress w celu wygenerowania linku.

        Returns:
            Tuple[bool, str]: (sukces: True/False, link_lub_komunikat_błędu)
        """
        if not self.wp_user or not self.wp_pass:
            return False, "Brak poświadczeń WP (WP_USER / WP_PASS)"

        endpoint = f"{self.wp_url}/wp-json/draft-collab/v1/generate"
        payload = {
            "post_id": post_id,
            "email": email,
            "expire_on_publish": expire_on_publish,
        }

        try:
            resp = requests.post(
                endpoint,
                json=payload,
                auth=(self.wp_user, self.wp_pass),
                headers={"Content-Type": "application/json"},
                timeout=15,
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                link = data.get("link") or data.get("url") or data.get("collab_link")
                if link:
                    return True, link
                return False, f"Brak pola link w odpowiedzi WP API: {data}"
            return False, f"Błąd WP API {resp.status_code}: {resp.text[:200]}"
        except requests.exceptions.RequestException as e:
            return False, f"Błąd połączenia z WP API: {str(e)}"

    def health_check(self) -> Dict[str, Any]:
        """Sprawdza konfigurację, dostępność Google Sheets API oraz WordPress REST API.

        Returns:
            Słownik ze statusem komponentów.
        """
        result: Dict[str, Any] = {
            "worker": "CollabLinker",
            "healthy": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": {
                "config": {"status": "ok", "missing": []},
                "google_sheets": {"healthy": False},
                "wordpress_api": {"healthy": False},
            },
        }

        # 1. Weryfikacja zmiennych środowiskowych
        missing = []
        if not self.sa_file:
            missing.append("GOOGLE_SA_FILE")
        if not self.sheet_id:
            missing.append("SHEETS_EMISJA_ID")
        if not self.wp_user:
            missing.append("WP_USER")
        if not self.wp_pass:
            missing.append("WP_PASS")

        if missing:
            result["checks"]["config"] = {
                "status": "warning" if len(missing) < 4 else "error",
                "missing": missing,
            }

        # 2. Test Google Sheets API
        try:
            sheets = self._get_sheets_service()
            if self.sheet_id:
                meta = (
                    sheets.spreadsheets()
                    .get(spreadsheetId=self.sheet_id, fields="spreadsheetId,properties.title")
                    .execute()
                )
                result["checks"]["google_sheets"] = {
                    "healthy": True,
                    "sheet_title": meta.get("properties", {}).get("title"),
                    "spreadsheet_id": self.sheet_id,
                }
            else:
                result["checks"]["google_sheets"] = {
                    "healthy": False,
                    "error": "Brak SHEETS_EMISJA_ID do przetestowania połączenia",
                }
        except Exception as e:
            result["checks"]["google_sheets"] = {
                "healthy": False,
                "error": str(e),
            }

        # 3. Test WordPress REST API & draft-collab
        try:
            auth = (self.wp_user, self.wp_pass) if (self.wp_user and self.wp_pass) else None
            wp_resp = requests.get(f"{self.wp_url}/wp-json/", auth=auth, timeout=10)
            if wp_resp.status_code == 200:
                wp_info = wp_resp.json()
                namespaces = wp_info.get("namespaces", [])
                has_draft_collab = "draft-collab/v1" in namespaces
                result["checks"]["wordpress_api"] = {
                    "healthy": True,
                    "wp_url": self.wp_url,
                    "authenticated": auth is not None,
                    "has_draft_collab_plugin": has_draft_collab,
                    "namespaces_count": len(namespaces),
                }
            else:
                result["checks"]["wordpress_api"] = {
                    "healthy": False,
                    "error": f"HTTP {wp_resp.status_code} z {self.wp_url}/wp-json/",
                }
        except Exception as e:
            result["checks"]["wordpress_api"] = {
                "healthy": False,
                "error": str(e),
            }

        sheets_ok = result["checks"]["google_sheets"]["healthy"]
        wp_ok = result["checks"]["wordpress_api"]["healthy"]
        result["healthy"] = sheets_ok and wp_ok

        return result

    def get_status(self) -> Dict[str, Any]:
        """Zwraca ostatni stan workera."""
        status_copy = dict(self._last_status)
        status_copy["worker"] = "CollabLinker"
        status_copy["config"] = {
            "wp_url": self.wp_url,
            "has_wp_user": bool(self.wp_user),
            "has_wp_pass": bool(self.wp_pass),
            "has_sa_file": bool(self.sa_file),
            "has_sheet_id": bool(self.sheet_id),
            "collab_email": self.collab_email,
        }
        return status_copy

    def process(self, task: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generuje linki draft-collab dla wierszy arkusza i zapisuje je z powrotem do arkusza.

        Args:
            task: Słownik parametrów zadania:
                - sheet_id (str): ID arkusza Google Sheets (opcjonalnie, default z env)
                - sheet_name (str): Nazwa zakładki (domyślnie 'Emisja')
                - wp_url_column (str): Nazwa kolumny z linkiem draftu WP (domyślnie 'WP Draft URL')
                - collab_column (str): Nazwa kolumny z linkiem collab (domyślnie 'Link draft')
                - collab_email (str): Email odbiorcy (domyślnie z env COLLAB_EMAIL lub tobroz@gmail.com)
                - expire_on_publish (bool): Czy link wygasa po publikacji (domyślnie False)
                - dry_run (bool): Jeśli True, nie zapisuje zmian do Google Sheets (domyślnie False)
                - force_refresh (bool): Jeśli True, nadpisuje istniejące już linki (domyślnie False)

        Returns:
            Dict[str, Any]: Statystyki wykonania w formacie:
                {
                    "status": "ok" / "error",
                    "processed": int,
                    "updated": int,
                    "failed": int,
                    "skipped": int,
                    "results": list
                }
        """
        task = task or {}
        sheet_id = task.get("sheet_id") or self.sheet_id
        sheet_name = task.get("sheet_name", "Emisja")
        wp_url_col_name = task.get("wp_url_column", "WP Draft URL")
        collab_col_name = task.get("collab_column", "Link draft")
        collab_email = task.get("collab_email") or self.collab_email
        expire_on_publish = bool(task.get("expire_on_publish", False))
        dry_run = bool(task.get("dry_run", False))
        force_refresh = bool(task.get("force_refresh", False))

        now_iso = datetime.now(timezone.utc).isoformat()
        self._last_status["last_run"] = now_iso
        self._last_status["status"] = "processing"

        if not sheet_id:
            error_msg = "Brak parametru sheet_id lub zmiennej SHEETS_EMISJA_ID"
            self.logger.error(error_msg)
            self._last_status["status"] = "error"
            self._last_status["error"] = error_msg
            return {
                "status": "error",
                "error": error_msg,
                "processed": 0,
                "updated": 0,
                "failed": 0,
                "skipped": 0,
                "results": [],
            }

        try:
            sheets = self._get_sheets_service()
        except Exception as e:
            self.logger.error("Błąd inicjalizacji klienta Google Sheets: %s", e)
            self._last_status["status"] = "error"
            self._last_status["error"] = str(e)
            return {
                "status": "error",
                "error": str(e),
                "processed": 0,
                "updated": 0,
                "failed": 0,
                "skipped": 0,
                "results": [],
            }

        # Pobierz dane arkusza z danymi siatki (includeGridData=True dla hiperlinków i formuł)
        self.logger.info("Pobieranie danych z arkusza '%s' (ID: %s)...", sheet_name, sheet_id)
        try:
            res = (
                sheets.spreadsheets()
                .get(spreadsheetId=sheet_id, ranges=[sheet_name], includeGridData=True)
                .execute()
            )
        except Exception as e:
            self.logger.error("Błąd pobierania arkusza '%s': %s", sheet_name, e)
            self._last_status["status"] = "error"
            self._last_status["error"] = str(e)
            return {
                "status": "error",
                "error": f"Błąd pobierania arkusza: {str(e)}",
                "processed": 0,
                "updated": 0,
                "failed": 0,
                "skipped": 0,
                "results": [],
            }

        sheet_list = res.get("sheets", [])
        if not sheet_list:
            error_msg = f"Arkusz '{sheet_name}' nie został odnaleziony w skoroszycie."
            self.logger.error(error_msg)
            return {
                "status": "error",
                "error": error_msg,
                "processed": 0,
                "updated": 0,
                "failed": 0,
                "skipped": 0,
                "results": [],
            }

        sheet_data = sheet_list[0].get("data", [])
        if not sheet_data:
            return {
                "status": "ok",
                "message": "Pusty arkusz",
                "processed": 0,
                "updated": 0,
                "failed": 0,
                "skipped": 0,
                "results": [],
            }

        row_data = sheet_data[0].get("rowData", [])
        if not row_data:
            return {
                "status": "ok",
                "message": "Brak wierszy w arkuszu",
                "processed": 0,
                "updated": 0,
                "failed": 0,
                "skipped": 0,
                "results": [],
            }

        # Odczytaj nagłówki z wiersza 0
        first_row_cells = row_data[0].get("values", [])
        headers = [cell.get("formattedValue", "").strip() for cell in first_row_cells]
        headers_lower = [h.lower() for h in headers]

        # 1. Znajdź indeks kolumny z URL draftu WP
        wp_url_col_idx = -1
        if wp_url_col_name in headers:
            wp_url_col_idx = headers.index(wp_url_col_name)
        elif wp_url_col_name.lower() in headers_lower:
            wp_url_col_idx = headers_lower.index(wp_url_col_name.lower())
        else:
            # Szukanie fallbackowe
            for idx, h in enumerate(headers_lower):
                if "wp draft" in h or ("draft" in h and "url" in h):
                    wp_url_col_idx = idx
                    break

        if wp_url_col_idx == -1:
            error_msg = f"Nie znaleziono kolumny '{wp_url_col_name}' w nagłówkach arkusza: {headers}"
            self.logger.error(error_msg)
            return {
                "status": "error",
                "error": error_msg,
                "processed": 0,
                "updated": 0,
                "failed": 0,
                "skipped": 0,
                "results": [],
            }

        # 2. Znajdź lub utwórz kolumnę 'Link draft'
        collab_col_idx = -1
        if collab_col_name in headers:
            collab_col_idx = headers.index(collab_col_name)
        elif collab_col_name.lower() in headers_lower:
            collab_col_idx = headers_lower.index(collab_col_name.lower())

        if collab_col_idx == -1:
            collab_col_idx = len(headers)
            col_letter = col_idx_to_letter(collab_col_idx)
            self.logger.info(
                "Kolumna '%s' nie istnieje. Dynamiczne dodawanie w kolumnie %s (indeks %d)...",
                collab_col_name,
                col_letter,
                collab_col_idx,
            )
            if not dry_run:
                try:
                    header_range = f"'{sheet_name}'!{col_letter}1"
                    sheets.spreadsheets().values().update(
                        spreadsheetId=sheet_id,
                        range=header_range,
                        valueInputOption="RAW",
                        body={"values": [[collab_col_name]]},
                    ).execute()
                    self.logger.info("Utworzono nagłówek '%s' w %s", collab_col_name, header_range)
                except Exception as e:
                    error_msg = f"Błąd tworzenia kolumny '{collab_col_name}': {e}"
                    self.logger.error(error_msg)
                    return {
                        "status": "error",
                        "error": error_msg,
                        "processed": 0,
                        "updated": 0,
                        "failed": 0,
                        "skipped": 0,
                        "results": [],
                    }
        else:
            col_letter = col_idx_to_letter(collab_col_idx)

        # 3. Iteracja po wierszach danych (od wiersza 2 w arkuszu -> index 1 w row_data)
        processed = 0
        updated = 0
        failed = 0
        skipped = 0
        results: List[Dict[str, Any]] = []
        updates: List[Dict[str, Any]] = []

        for row_idx, row in enumerate(row_data[1:], start=2):
            values = row.get("values", [])

            # Sprawdź czy wiersz ma kolumnę WP Draft URL
            if len(values) <= wp_url_col_idx:
                continue

            cell_wp = values[wp_url_col_idx]
            url = self._extract_url_from_cell(cell_wp)

            if not url:
                continue

            processed += 1

            # Sprawdź czy link collab już istnieje w tym wierszu
            existing_collab = ""
            if len(values) > collab_col_idx:
                existing_cell = values[collab_col_idx]
                existing_collab = existing_cell.get("formattedValue", "").strip()

            if existing_collab and existing_collab.startswith("http") and not force_refresh:
                self.logger.debug("Wiersz %d: link już istnieje (%s) — pomijam", row_idx, existing_collab[:40])
                skipped += 1
                results.append({
                    "row": row_idx,
                    "status": "skipped",
                    "reason": "already_exists",
                    "url": url,
                    "link": existing_collab,
                })
                continue

            # Wyodrębnij ID wpisu WordPress
            post_id = self._extract_post_id_from_url(url)
            if not post_id:
                err = f"Nie udało się ustalić WP post_id z URL: {url}"
                self.logger.warning("Wiersz %d: %s", row_idx, err)
                failed += 1
                results.append({
                    "row": row_idx,
                    "status": "failed",
                    "error": err,
                    "url": url,
                })
                continue

            # Generuj link draft-collab
            self.logger.info("Wiersz %d: Generowanie linku dla post_id=%d (%s)...", row_idx, post_id, collab_email)
            ok, link_or_err = self._generate_collab_link(
                post_id=post_id,
                email=collab_email,
                expire_on_publish=expire_on_publish,
            )

            if not ok:
                self.logger.error("Wiersz %d: Błąd generowania linku: %s", row_idx, link_or_err)
                failed += 1
                results.append({
                    "row": row_idx,
                    "post_id": post_id,
                    "status": "failed",
                    "error": link_or_err,
                    "url": url,
                })
                continue

            # Sukces
            updated += 1
            results.append({
                "row": row_idx,
                "post_id": post_id,
                "status": "updated",
                "link": link_or_err,
                "url": url,
            })

            target_range = f"'{sheet_name}'!{col_letter}{row_idx}"
            if not dry_run:
                updates.append({
                    "range": target_range,
                    "values": [[link_or_err]],
                })
            else:
                self.logger.info("[DRY RUN] Would update %s -> %s", target_range, link_or_err)

        # 4. Zapisz wygenerowane linki wsadowo do arkusza Google
        if updates and not dry_run:
            self.logger.info("Zapisywanie %d linków do arkusza '%s'...", len(updates), sheet_name)
            try:
                sheets.spreadsheets().values().batchUpdate(
                    spreadsheetId=sheet_id,
                    body={"valueInputOption": "RAW", "data": updates},
                ).execute()
                self.logger.info("Pomyślnie zaktualizowano %d komórek w arkuszu.", len(updates))
            except Exception as e:
                error_msg = f"Błąd podczas batchUpdate w Google Sheets: {e}"
                self.logger.error(error_msg)
                self._last_status["status"] = "error"
                self._last_status["error"] = error_msg
                return {
                    "status": "error",
                    "error": error_msg,
                    "processed": processed,
                    "updated": 0,
                    "failed": failed + updated,
                    "skipped": skipped,
                    "results": results,
                }

        final_status = "ok" if failed == 0 else ("partial" if updated > 0 else "error")
        summary = {
            "status": final_status,
            "processed": processed,
            "updated": updated,
            "failed": failed,
            "skipped": skipped,
            "results": results,
        }

        self._last_status["status"] = final_status
        self._last_status["last_result"] = summary
        self._last_status["error"] = None if final_status in ("ok", "partial") else "Niektóre wiersze zwróciły błąd"

        return summary
