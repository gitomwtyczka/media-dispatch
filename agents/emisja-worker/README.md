# emisja-worker

> Moduł automatyzacji arkusza emisyjnego oraz generowania linków współdzielenia wersji roboczych (draft-collab) dla portalu Prawy.pl (WordPress).  
> Część Warstwy 2 (Editorial) i Warstwy 3 (Production) w architekturze `media-dispatch`.

---

## 1. Co robi `emisja-worker`

W procesie wydawniczym `media-dispatch` artykuły wygenerowane przez silniki VSE i PressAI trafiają do WordPress jako wersje robocze (`draft`). Ich status oraz adresy URL są rejestrowane w arkuszu Google Sheets w zakładce **"Emisja"**.

Główne zadania modułu:
1. **Synchronizacja statusów i treści**: obsługa wstrzykiwania treści i mediów do WordPress (`emisja_sheets_sync.py`).
2. **Generowanie linków kolaboracyjnych (`collab_linker.py`)**:
   - Odczytuje wiersze arkusza ze szczegółowymi danymi komórek (`includeGridData=True`), poprawnie interpretując formuły `=HYPERLINK("...")` oraz standardowe adresy URL.
   - Weryfikuje obecność kolumny docelowej **"Link draft"** — jeśli kolumna nie istnieje, tworzy ją dynamicznie w arkuszu.
   - Wyodrębnia identyfikator wpisu WordPress (`post_id`) z parametrów URL (`?p=ID`, `post=ID`, `preview_id=ID`) lub odnajduje go po slugu w WP REST API.
   - Wywołuje endpoint wtyczki WordPress `draft-collab` (`/wp-json/draft-collab/v1/generate`), generując unikalny tokenizowany link podglądu dla wskazanego adresu email współpracownika/redaktora.
   - Zapisuje wygenerowane linki wsadowo (`batchUpdate`) z powrotem do arkusza Google Sheets, pomijając wiersze posiadające już aktualny link.

---

## 2. Wymagania systemowe

1. **Wtyczka WordPress `draft-collab`**:
   - Zainstalowana i aktywna w serwisie WordPress (Prawy.pl).
   - Dostępny publicznie endpoint REST: `POST /wp-json/draft-collab/v1/generate`.
2. **Google Cloud Service Account**:
   - Plik klucza JSON konta serwisowego Google.
   - Zakres uprawnień: `https://www.googleapis.com/auth/spreadsheets`.
   - Arkusz Google Sheets musi być udostępniony adresowi email konta serwisowego z uprawnieniami edytora.
3. **WordPress Application Password**:
   - Użytkownik z uprawnieniami co najmniej `Editor` lub `Administrator`.
   - Wygenerowane hasło aplikacji w profilu WordPress (Application Password).
4. **Środowisko Python 3.10+**:
   - Zależności: `google-api-python-client`, `google-auth`, `requests`, `gspread`.

---

## 3. Zmienne środowiskowe (Environment Variables)

> ⛔ **BEZWZGLĘDNA ZASADA BEZPIECZEŃSTWA**: Żadne poświadczenia, klucze ani identyfikatory arkuszy nie mogą być hardkodowane w kodzie źródłowym repozytorium. Wszystkie konfiguracje i sekrety należy przekazywać przez zmienne środowiskowe.

| Zmienna | Typ | Wymagana | Domyślnie | Opis |
|---------|-----|----------|-----------|------|
| `GOOGLE_SA_FILE` | ścieżka | **TAK** | — | Ścieżka do pliku klucza Service Account JSON (np. `/home/ubuntu/service-account.json`) |
| `SHEETS_EMISJA_ID` | str | **TAK** | — | Identyfikator arkusza Google Sheets (Spreadsheet ID) |
| `WP_URL` | url | NIE | `https://prawy.pl` | Bazowy URL instancji WordPress |
| `WP_USER` | str | **TAK** | — | Nazwa użytkownika WordPress do autoryzacji REST API |
| `WP_PASS` | str | **TAK** | — | Hasło aplikacji WordPress (Application Password) |
| `COLLAB_EMAIL` | email | NIE | `tobroz@gmail.com` | Adres email współpracownika, dla którego generowany jest link |

---

## 4. Użycie w kodzie (Python API)

### Inicjalizacja i wywołanie `CollabLinker`

```python
from agents.emisja_worker.collab_linker import CollabLinker

# Inicjalizacja pobiera konfigurację z env vars
linker = CollabLinker()

# 1. Health check
health = linker.health_check()
print("Status połączeń:", health)

# 2. Przetworzenie arkusza
task = {
    "sheet_name": "Emisja",
    "wp_url_column": "WP Draft URL",
    "collab_column": "Link draft",
    "collab_email": "tobroz@gmail.com",
    "expire_on_publish": False,
    "dry_run": False,        # True = test bez zapisu do arkusza
    "force_refresh": False   # True = nadpisuj nawet jeśli link już istnieje
}

result = linker.process(task)
print(f"Wynik: zaktualizowano {result['updated']}, pominięto {result['skipped']}, błędy {result['failed']}")
```

### Użycie standardowego interfejsu workera (`worker.py`)

```python
from agents.emisja_worker.worker import health_check, process, get_status

# Test połączenia
status = health_check()

# Wykonanie zadania z domyślnymi parametrami
summary = process({"dry_run": True})
```

---

## 5. Uruchamianie z wiersza poleceń (CLI)

Moduł `worker.py` zawiera pełnoprawny interfejs CLI:

```powershell
# 1. Sprawdzenie stanu połączeń z Google Sheets i WP API
python -m agents.emisja_worker.worker --health

# 2. Uruchomienie w trybie symulacji (dry-run — bezpieczny test bez zapisu w Sheets)
python -m agents.emisja_worker.worker --dry-run

# 3. Pełne wykonanie na domyślnym arkuszu z env vars
python -m agents.emisja_worker.worker

# 4. Nadpisanie parametrów w CLI
python -m agents.emisja_worker.worker \
  --sheet-id "1zqwvS784EaZh1EJIcXk1DliAau1r4X15ENFJjloDSaM" \
  --sheet-name "Emisja" \
  --email "redaktor@prawy.pl" \
  --expire-on-publish \
  --force
```

---

## 6. Format zadania i odpowiedzi

### Struktura wejściowa `task`

```json
{
  "sheet_id": "1zqwvS...",
  "sheet_name": "Emisja",
  "wp_url_column": "WP Draft URL",
  "collab_column": "Link draft",
  "collab_email": "tobroz@gmail.com",
  "expire_on_publish": false,
  "dry_run": false,
  "force_refresh": false
}
```

### Struktura wyjściowa `result`

```json
{
  "status": "ok",
  "processed": 5,
  "updated": 3,
  "failed": 0,
  "skipped": 2,
  "results": [
    {
      "row": 2,
      "post_id": 14521,
      "status": "updated",
      "link": "https://prawy.pl/?draft_collab=abc123xyz...",
      "url": "https://prawy.pl/wp-admin/post.php?post=14521&action=edit"
    },
    {
      "row": 3,
      "status": "skipped",
      "reason": "already_exists",
      "url": "https://prawy.pl/?p=14522",
      "link": "https://prawy.pl/?draft_collab=def456..."
    }
  ]
}
```

---

## 7. Struktura plików modułu

```
agents/emisja-worker/
├── __init__.py               # Eksport klas i funkcji publicznych
├── collab_linker.py          # Główna klasa CollabLinker (logika Sheets + WP REST API)
├── emisja_sheets_sync.py     # Pipeline wstrzykiwania treści z YT/arkusza do WP
├── worker.py                 # Standardowy interfejs i CLI workera
├── constitution.md           # Konstytucja operacyjna dla agentów AI
└── README.md                 # Niniejsza dokumentacja
```
