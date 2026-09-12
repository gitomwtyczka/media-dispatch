# Raport: Implementacja emisja-worker (CollabLinker)

| Pole | Wartość |
|------|---------|
| **Data** | 12.09.2026 |
| **Agent / Callsign** | `media-dev-D` |
| **Zadanie** | Budowa pełnoprawnego `emisja-worker/collab_linker.py`, `worker.py`, `README.md`, `constitution.md` |
| **Status** | ✅ DONE |

---

## 1. Zakres wykonanych prac

Zgodnie ze specyfikacją dispatchu zaimplementowano i wypchnięto na GitHub do repozytorium `gitomwtyczka/media-dispatch` (branch: `main`):

1. **`agents/emisja-worker/collab_linker.py`** (commit: `9808e4a8fd7be9e409901a47fa19c400eea05559`):
   - Klasa `CollabLinker` implementująca metody:
     - `health_check() -> dict` — weryfikacja konfiguracji env vars, połączenia do Google Sheets API (pobranie metadanych skoroszytu) oraz WordPress REST API (przestrzeń `draft-collab/v1` i autentykacja).
     - `process(task: dict) -> dict` — pełny proces pobierania wierszy z Google Sheets (`includeGridData=True`), parsowania formuł `=HYPERLINK`, dynamicznego tworzenia brakującej kolumny `Link draft`, wyodrębniania `post_id` (z query params `?p=`, `post=`, `preview_id=` lub przez WP REST API po slugu), wywołania WP pluginu `POST /wp-json/draft-collab/v1/generate` oraz wsadowego zapisu `batchUpdate`.
     - `get_status() -> dict` — status ostatniego uruchomienia i konfiguracji.
   - Dynamiczna konwersja indeksów kolumn do notacji literowej A1 (`col_idx_to_letter`), obsługująca kolumny poza Z (AA, AB, etc.).
   - Idempotentność: wiersze posiadające już poprawny link `http...` są pomijane (`skipped`), z opcją wymuszenia (`force_refresh=True`).
   - Obsługa flagi `dry_run=True` do bezpiecznego testowania bez zapisu do arkusza Google.

2. **`agents/emisja-worker/worker.py`** (commit: `6e8471563d438114a591a83f8fca1c3f854b7132`):
   - Standardowy wrapper funkcyjny: `health_check()`, `process(task)`, `get_status()`.
   - Interfejs CLI z obsługą argumentów: `--dry-run`, `--health`, `--status`, `--sheet-id`, `--sheet-name`, `--wp-url-col`, `--collab-col`, `--email`, `--expire-on-publish`, `--force`.

3. **`agents/emisja-worker/__init__.py`** (commit: `3ad19eda4629af5831ce67427b9483c8dcfd8c05`):
   - Pakiet Pythona z eksportem `CollabLinker`, `health_check`, `process`, `get_status`.

4. **`agents/emisja-worker/README.md`** (commit: `0e75afa9124eb8e4df0523f07a0976fa52401825`):
   - Szczegółowa dokumentacja: cel modułu, wymagania wstępne (wtyczka WordPress draft-collab, Google Service Account, Application Password), specyfikacja zmiennych środowiskowych, przykłady użycia w Pythonie i CLI, schematy formatów wejścia i wyjścia.

5. **`agents/emisja-worker/constitution.md`** (commit: `52d8d8034b72810d2d23bb95dd071d00995b7ccb`):
   - Konstytucja operacyjna modułu wzorowana na standardzie `agents/transcribe-worker/constitution.md`.
   - Szczegółowo opisane pułapki P1-P7: dynamiczne tworzenie kolumny, obsługa formuł `=HYPERLINK`, bezwzględny zakaz wycieków sekretów w repozytorium, wymóg autoryzacji przy odczycie draftów po slugu, różnorodne formaty URL, ochrona przed nadpisywaniem (idempotentność) i tryb dry-run.

---

## 2. Weryfikacja bezpieczeństwa (Zero Leaks)

- W kodzie **NIE ZNAJDUJĄ SIĘ** żadne wrażliwe dane (hasła WP Application Password, nazwy użytkowników, klucze konta serwisowego ani twardo zakodowane ID arkusza).
- Wszystkie parametry uwierzytelniające pobierane są wyłącznie ze zmiennych środowiskowych:
  - `GOOGLE_SA_FILE`
  - `SHEETS_EMISJA_ID`
  - `WP_URL` (domyślnie `https://prawy.pl`)
  - `WP_USER`
  - `WP_PASS`
  - `COLLAB_EMAIL`
- Istniejący plik `agents/emisja-worker/emisja_sheets_sync.py` pozostał nienaruszony.

---

## 3. Lista commitów na GitHub (`gitomwtyczka/media-dispatch`)

- `9808e4a8fd7be9e409901a47fa19c400eea05559` — `feat(emisja-worker): implement CollabLinker class [media-dev-D]`
- `6e8471563d438114a591a83f8fca1c3f854b7132` — `feat(emisja-worker): implement worker.py interface and CLI [media-dev-D]`
- `3ad19eda4629af5831ce67427b9483c8dcfd8c05` — `feat(emisja-worker): add __init__.py package definition [media-dev-D]`
- `0e75afa9124eb8e4df0523f07a0976fa52401825` — `docs(emisja-worker): add comprehensive README.md [media-dev-D]`
- `52d8d8034b72810d2d23bb95dd071d00995b7ccb` — `docs(emisja-worker): add constitution.md [media-dev-D]`

---

*media-dev-D | 12.09.2026*
