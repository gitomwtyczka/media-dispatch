# emisja-worker — Konstytucja

> Plik operacyjny dla agentów AI wywołujących i zarządzających emisja-worker.  
> Ostatnia aktualizacja: 12.09.2026 | media-dev-D

---

## 1. Tożsamość

| Pole | Wartość |
|------|---------|
| **Callsign** | `emisja-worker` / `collab-linker` |
| **Warstwa** | Warstwa 2 (Editorial) & Warstwa 3 (Production) |
| **Stack** | Python 3.12 · Google Sheets API v4 (`includeGridData=True`) · WordPress REST API · draft-collab plugin |
| **Środowisko** | VPS (`ubuntu@147.224.162.100`) / Docker / CLI |
| **Skrypty** | `agents/emisja-worker/collab_linker.py`, `agents/emisja-worker/worker.py` |

---

## 2. Jak wywołać

### Składnia bazowa

```powershell
# Bezpośrednie uruchomienie przez Pythona
python -m agents.emisja_worker.worker [flagi]
```

### Flagi CLI

| Flaga | Typ | Domyślnie | Opis |
|-------|-----|-----------|------|
| `--dry-run` | flag | off | Tryb bezpieczny / symulacja — brak zapisu do Google Sheets |
| `--health` | flag | off | Weryfikacja połączeń i konfiguracji (Sheets + WordPress) |
| `--status` | flag | off | Wyświetla stan ostatniego uruchomienia w formacie JSON |
| `--sheet-id` | str | `SHEETS_EMISJA_ID` | ID skoroszytu Google Sheets |
| `--sheet-name` | str | `Emisja` | Nazwa zakładki w arkuszu |
| `--wp-url-col` | str | `WP Draft URL` | Nazwa kolumny zawierającej linki do draftów WP |
| `--collab-col` | str | `Link draft` | Nazwa kolumny docelowej dla wygenerowanych linków |
| `--email` | str | `COLLAB_EMAIL` | Adres email współpracownika do autoryzacji podglądu |
| `--expire-on-publish` | flag | off | Wygaszenie linku natychmiast po opublikowaniu wpisu |
| `--force` | flag | off | Wymuszenie wygenerowania linków dla wierszy posiadających już link |

### Przykłady gotowych komend

```powershell
# 1. Sprawdzenie gotowości środowiska (health check)
python -m agents.emisja_worker.worker --health

# 2. Bezpieczny test w trybie dry-run (symulacja)
python -m agents.emisja_worker.worker --dry-run

# 3. Pełny przebieg produkcyjny
python -m agents.emisja_worker.worker

# 4. Przebieg dla niestandardowej zakładki i dedykowanego emaila współpracownika
python -m agents.emisja_worker.worker --sheet-name "Ostatnie niepubliczne" --email "korektor@prawy.pl" --expire-on-publish
```

---

## 3. Format wejścia i wyjścia

### Słownik zadania `task` (dla metody `process()`)

```python
task = {
    "sheet_id": "1zqwvS...",       # opcjonalne, default z env SHEETS_EMISJA_ID
    "sheet_name": "Emisja",         # domyślnie "Emisja"
    "wp_url_column": "WP Draft URL",# domyślnie "WP Draft URL"
    "collab_column": "Link draft",  # domyślnie "Link draft"
    "collab_email": "tobroz@gmail.com", # default z env COLLAB_EMAIL
    "expire_on_publish": False,
    "dry_run": False,               # True = brak zapisu do Sheets
    "force_refresh": False          # True = nadpisuj istniejące linki
}
```

### Słownik wyniku `result`

```python
{
    "status": "ok",      # "ok" / "partial" / "error"
    "processed": 5,      # przetworzone wiersze posiadające URL WP
    "updated": 3,        # pomyślnie wygenerowane i zapisane linki
    "failed": 0,         # nieudane wiersze
    "skipped": 2,        # pominięte (np. link już istniał)
    "results": [
        {
            "row": 2,
            "post_id": 14521,
            "status": "updated",
            "link": "https://prawy.pl/?draft_collab=abc...",
            "url": "https://prawy.pl/wp-admin/post.php?post=14521&action=edit"
        },
        {
            "row": 3,
            "status": "skipped",
            "reason": "already_exists",
            "url": "https://prawy.pl/?p=14522",
            "link": "https://prawy.pl/?draft_collab=def..."
        }
    ]
}
```

---

## 4. Wymagane uprawnienia i środowisko

1. **Google Cloud Service Account**:
   - Ścieżka do pliku klucza przekazywana przez zmienną środowiskową `GOOGLE_SA_FILE`.
   - Zakres uprawnień: `https://www.googleapis.com/auth/spreadsheets`.
   - Dostęp do arkusza nadany na adres konta serwisowego.
2. **WordPress REST API & Application Password**:
   - Dostęp administracyjny / edytorski przez poświadczenia `WP_USER` oraz `WP_PASS`.
   - Autoryzacja Basic Auth nagłówkiem `Authorization` w żądaniach HTTP.
3. **Wtyczka WordPress draft-collab**:
   - Endpoint: `POST /wp-json/draft-collab/v1/generate`.
   - Parametry: `post_id` (int), `email` (string), `expire_on_publish` (bool).
   - Zwraca JSON: `{"link": "https://prawy.pl/?draft_collab=..."}`.

---

## 5. Integracja z pipeline media-dispatch

```
[VSE / PressAI]
       │
       ▼ (wstrzykuje artykuł)
[WordPress Draft (post_id)]
       │
       ▼ (zapisuje URL draftu)
[Google Sheets: Zakładka "Emisja" (kolumna "WP Draft URL")]
       │
       ▼
[emisja-worker / CollabLinker]
  ├── Odczyt komórek z GridData (formuły =HYPERLINK i parametry URL)
  ├── Weryfikacja/utworzenie kolumny "Link draft"
  ├── Wywołanie WP REST API draft-collab
  └── Zapis linku wsadowo (batchUpdate) do kolumny "Link draft"
       │
       ▼
[Redaktor Naczelny / Korektor / Autorzy] (podgląd i akceptacja bez konta WP)
```

---

## 6. Znane pułapki operacyjne

### P1 — Brak kolumny "Link draft" w arkuszu
W niektórych arkuszach kolumna na linki draftu może nie istnieć w momencie uruchomienia.
Skrypt **musi dynamicznie wykryć brak nagłówka**, obliczyć indeks nowej kolumny na końcu nagłówków, przekonwertować go do notacji literowej A1 (uwzględniając kolumny poza Z, np. AA, AB) i wstawić nagłówek przed zapisem wierszy danych.

### P2 — Formuły `=HYPERLINK` i ukryte adresy URL
Google Sheets często przechowuje linki w postaci formuł `=HYPERLINK("https://...", "Tekst")` lub jako ukryty obiekt `hyperlink` w metadanych komórki. Zwykłe pobranie wartości tekstowych (`values().get()`) gubi adres docelowy.
Wymagane jest użycie `spreadsheets().get(..., includeGridData=True)` i hierarchiczne parsowanie: `cell.get('hyperlink')` → formuła `userEnteredValue.formulaValue` → `formattedValue`.

### P3 — Wycieki danych uwierzytelniających (ABSOLUTNA ZASADA)
Nigdy nie wolno umieszczać poświadczeń (hasła WordPress Application Password, kluczy JSON ani Spreadsheet ID) bezpośrednio w kodzie źródłowym commita. Wszystkie sekrety muszą pochodzić wyłącznie ze zmiennych środowiskowych (`WP_USER`, `WP_PASS`, `GOOGLE_SA_FILE`, `SHEETS_EMISJA_ID`).

### P4 — Wyszukiwanie post_id w WP REST API wymaga autentykacji
W przypadku adresów URL zawierających tylko slug (np. `https://prawy.pl/wiadomosci/slug-artykulu/`), zapytanie o post wymaga uprawnień do odczytu draftów (`status=draft,pending,private,future,publish`). Niezautoryzowane zapytanie do WordPress zwróci pustą listę postów.

### P5 — Różne formaty linków do postów
Linki w arkuszu mogą pochodzić z różnych źródeł:
- Panel WP: `.../post.php?post=12345&action=edit`
- Podgląd: `.../?p=12345` lub `.../?preview_id=12345`
- Link kanoniczny: `.../tytul-wpisu/`
Parser musi obsłużyć parametry query string, wyrażenia regularne oraz fallback po slugu.

### P6 — Idempotentność i ochrona przed nadpisywaniem
Ponowne uruchomienie workera nie powinno od nowa generować linków dla wierszy, które już posiadają poprawny link kolaboracyjny (zaczynający się od `http`). Domyślnie takie wiersze są pomijane (`skipped`), chyba że podano flagę `force_refresh=True`.

### P7 — Bezpieczeństwo testów (dry-run)
Przed uruchomieniem masowej aktualizacji arkusza produkcyjnego zawsze należy przeprowadzić weryfikację z flagą `--dry-run`, aby potwierdzić poprawność parsowania wierszy i generowania linków bez modyfikacji danych w Google Sheets.

---

## 7. Raport po zakończeniu

Agent AI raportuje do Supervisora w formacie:

```
[emisja-worker | DD.MM.YYYY HH:MM] STATUS

Arkusz: <sheet_name> (ID: <sheet_id>)
Kolumna źródłowa: <wp_url_column>
Kolumna docelowa: <collab_column>
Email: <collab_email>

Wynik:
  - Przetworzono: X wierszy
  - Zaktualizowano: Y linków
  - Pominięto: Z wierszy
  - Błędy: N

Status: OK / ERROR
```

---

## 8. Architektura modułu

```
agents/emisja-worker/
├── __init__.py           # Interfejs pakietu
├── collab_linker.py      # Klasa CollabLinker (Sheets API + WP REST API)
├── worker.py             # health_check(), process(), get_status(), CLI
├── emisja_sheets_sync.py # Istniejący proces synchronizacji YT/VSE z arkuszem
├── constitution.md       # Niniejsza konstytucja
└── README.md             # Dokumentacja modułu
```

---

*Inicjacja: media-dev-D | 12.09.2026*
