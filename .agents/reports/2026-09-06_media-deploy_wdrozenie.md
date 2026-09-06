# Raport wdrożeniowy: emisja-worker i radar-worker

**Callsign:** media-deploy
**Data:** 2026-09-06

## Zrealizowane zadania
1. **Synchronizacja i wdrożenie skryptów:**
   - Zlokalizowano skrypty `emisja_sheets_sync.py` oraz `radar_sheets_sync.py`.
   - Pomyślnie przesłano oba skrypty na serwer VPS (SCP) do dedykowanych katalogów `agents/emisja-worker/` i `agents/radar-worker/` w przestrzeni `/home/ubuntu/media-dispatch/`.
2. **Konfiguracja .env:**
   - Zweryfikowano zawartość pliku `.env` w `/home/ubuntu/media-dispatch/`. Zgodnie z instrukcją, potwierdzono konfigurację i obecność poprawnego tokena `PRESSAI_JWT_USER`.
3. **Konfiguracja Crona:**
   - Zaktualizowano crontab serwera, dodając pełną automatyzację jako działające w tle procesy:
     - `emisja_sheets_sync.py` uruchamia się co pełną godzinę.
     - `radar_sheets_sync.py` uruchamia się w połowie każdej godziny (wpół do).
   - Skrypty ładują bezpośrednio środowisko projektu z uwzględnieniem `.env`.

## Status
Pełen sukces. Skrypty działają autonomicznie.