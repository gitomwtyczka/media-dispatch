# Raport: Rozłączenie media-dispatch od muzeum SA (migracja SA)

**Data:** 2026-09-08
**Callsign:** sa-migration-01
**Supervisor:** Supervisor 03
**Status:** Zakończone sukcesem (izolacja lokalna plikowa + .env)

---

## 1. Kluczowe parametry i dane SA

- **SA_CLIENT_EMAIL:** `muzeum-drive-reader@antigravity-mcp-keys.iam.gserviceaccount.com`
- **SA_PROJECT_ID:** `antigravity-mcp-keys`
- **STATUS GCLOUD:** `GCLOUD_NIEDOSTEPNY — tymczasowo używamy kopii muzeum SA, wymaga manualnego utworzenia nowego SA w GCP Console`
- **Ścieżka do klucza SA w media-dispatch:** `/home/ubuntu/media-dispatch/config/service_account.json` (uprawnienia 600)

> ℹ️ **Uwaga dotycząca Google Sheets:** Ponieważ `gcloud` nie jest zainstalowany na VPS i tymczasowo używamy wyizolowanej kopii z projektu muzeum, dotychczasowy email (`muzeum-drive-reader@antigravity-mcp-keys.iam.gserviceaccount.com`) posiada już uprawnienia edytora do obecnych arkuszy. Gdy nowe konto serwisowe zostanie wygenerowane w GCP Console (np. `media-dispatch-sheets@...`), wystarczy podmienić plik `/home/ubuntu/media-dispatch/config/service_account.json` i udostępnić mu arkusze Google.

---

## 2. Wykonane kroki

1. **KROK 0 (Audyt):**
   - Plik źródłowy: `/home/ubuntu/otwock-data/muzeum/muzeum-drive-sa.json` istnieje.
   - `gcloud` nie jest zainstalowany w PATH na VPS (`GCLOUD_BRAK`).
   - W `/home/ubuntu/media-dispatch/.env` brakowało wpisów `GOOGLE_SA*`.
2. **KROK 1 (Izolacja - kopia lokalna):**
   - Utworzono dedykowany katalog `/home/ubuntu/media-dispatch/config`.
   - Skopiowano klucz do `/home/ubuntu/media-dispatch/config/service_account.json`.
   - Ustawiono uprawnienia `chmod 600`.
3. **KROK 2 (Konto serwisowe GCP):**
   - Zgodnie z instrukcją dla scenariusza braku `gcloud`, pominięto tworzenie nowego SA z poziomu CLI (wymaga GCP Console). Zastosowano rozwiązanie z KROKU 1.
4. **KROK 3 (Aktualizacja .env na VPS):**
   - Zaktualizowano `/home/ubuntu/media-dispatch/.env`:
     ```env
     GOOGLE_SA_KEY_PATH=/home/ubuntu/media-dispatch/config/service_account.json
     GOOGLE_SA_FILE=/home/ubuntu/media-dispatch/config/service_account.json
     ```
5. **KROK 4 (Repozytorium .env.example):**
   - Utworzono `.env.example` w repozytorium `gitomwtyczka/media-dispatch` (branch `main`).
6. **KROK 5 (Audyt referencji w skryptach):**
   - Przeszukano kod pod kątem twardych odwołań do muzeum.
7. **KROK 6 (Weryfikacja):**
   - Przetestowano ładowanie `.env` i odczyt klucza SA w środowisku Pythona na VPS. Wynik: `OK`.

---

## 3. Stan zmiennych środowiskowych na VPS (.env)

```env
GOOGLE_SA_KEY_PATH=/home/ubuntu/media-dispatch/config/service_account.json
GOOGLE_SA_FILE=/home/ubuntu/media-dispatch/config/service_account.json
```

---

## 4. Wykryte hardcoded ścieżki do muzeum (eskalacja do Supervisora)

1. **`agents/sheets-sync-worker/apply_kandydaci_formatting.py:45`**
   - Wprost podana ścieżka `/home/ubuntu/otwock-data/muzeum/muzeum-drive-sa.json` bez sprawdzania zmiennych środowiskowych.
2. **`agents/radar-worker/radar_sheets_sync.py:12`**
   - `SERVICE_ACC = os.environ.get("GOOGLE_SA_KEY_PATH", "/home/ubuntu/otwock-data/muzeum/muzeum-drive-sa.json")` (używa env var, stary fallback).
3. **`agents/kurier365-worker/worker.py:179, 723` oraz `231`**
   - `sa_file = os.getenv('GOOGLE_SA_FILE', '/home/ubuntu/otwock-data/muzeum/muzeum-drive-sa.json')` (używa env var, stary fallback).
4. **`agents/emisja-worker/emisja_sheets_sync.py:17`**
   - Zahardcodowana ścieżka lokalna Windows: `C:\Users\tomas2\.gemini\antigravity\playground\media-dispatch\agents\sheets-sync-worker\service_account.json`.

---

## 5. Wynik testu weryfikacyjnego (KROK 6)

```text
SA PATH: /home/ubuntu/media-dispatch/config/service_account.json
SA EMAIL: muzeum-drive-reader@antigravity-mcp-keys.iam.gserviceaccount.com
PROJECT: antigravity-mcp-keys
OK
```
