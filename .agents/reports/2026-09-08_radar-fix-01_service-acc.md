# Raport wykonania: Fix SERVICE_ACC path w radar_sheets_sync.py

**Callsign:** radar-fix-01  
**Supervisor:** Supervisor 03 | sesja 08.09.2026  
**Repo:** gitomwtyczka/media-dispatch (branch: main)  
**Commit SHA:** 737ff3d68c652312f8b64255841242cb48ea52db  
**Status:** PASS  

---

## 1. Zmiana w kodzie
W pliku `agents/radar-worker/radar_sheets_sync.py` zastąpiono zahardkodowaną ścieżkę Windows do pliku service account elastyczną konfiguracją pobieraną ze zmiennej środowiskowej z domyślną ścieżką Linux:
```python
SERVICE_ACC = os.environ.get("GOOGLE_SA_KEY_PATH", "/home/ubuntu/otwock-data/muzeum/muzeum-drive-sa.json")
```

## 2. Weryfikacja na GitHub & Deploy VPS
- Commit został wypchnięty do `gitomwtyczka/media-dispatch` (`main`): `737ff3d68c652312f8b64255841242cb48ea52db`
- Wykonano `git pull origin main` na serwerze Oracle VPS (`/home/ubuntu/media-dispatch`), gałąź zaktualizowana `Fast-forward` do `737ff3d`.

## 3. Wynik testu na VPS
Test wykonany komendą:
```bash
set -a && source .env && set +a && python3 agents/radar-worker/radar_sheets_sync.py 2>&1 | head -30
```

Logi wykonania:
```text
/usr/lib/python3/dist-packages/requests/__init__.py:87: RequestsDependencyWarning: urllib3 (2.6.3) or chardet (4.0.0) doesn't match a supported version!
  warnings.warn("urllib3 ({}) or chardet ({}) doesn't match a supported "
Start: radar_sheets_sync.py
--- TRYB FETCH: Pobieranie trendów z Content Radar ---
Nie można pobrać tokenu cr-api (Brak tokenu CONTENT_RADAR_JWT w .env). Pomijam pobieranie z Radaru.

--- TRYB PUBLISH: Szukanie zadań w zakładce ---

Processing row 2: Japonia buduje centrum AI
  [2] Generowanie artykułu...
  [3] Zapisywanie do historii PressAI...
  [BŁĄD] Zapis historii: {"detail":[{"type":"missing","loc":["body","portal"],"msg":"Field required","input":{"portal_id":"2b047d7d-15a1-4d2f-8463-f89c2275bb73","content":"❌ Brak tekstu źródłowego i instrukcji.\n\nAby wygener

Processing row 3: Bernie Sanders przeciw AI
  [2] Generowanie artykułu...
  [3] Zapisywanie do historii PressAI...
  [BŁĄD] Zapis historii: {"detail":[{"type":"missing","loc":["body","portal"],"msg":"Field required","input":{"portal_id":"2b047d7d-15a1-4d2f-8463-f89c2275bb73","content":"❌ Brak tekstu źródłowego i instrukcji.\n\nAby wygener

Processing row 4: Fuzja herbariów ratuje historię
  [2] Generowanie artykułu...
  [3] Zapisywanie do historii PressAI...
  [BŁĄD] Zapis historii: {"detail":[{"type":"missing","loc":["body","portal"],"msg":"Field required","input":{"portal_id":"2b047d7d-15a1-4d2f-8463-f89c2275bb73","content":"❌ Brak tekstu źródłowego i instrukcji.\n\nAby wygener

Processing row 6: Tropical cyclones could be predicted with an extra day’s warning, thanks to an AI model
  [1] Extracting URL...
  [2] Generowanie artykułu...
  [3] Zapisywanie do historii PressAI...
  [BŁĄD] Zapis historii: {"detail":[{"type":"missing","loc":["body","portal"],"msg":"Field required","input":{"portal_id":"2b047d7d-15a1-4d2f-8463-f89c2275bb73","content":"Przepraszam, ale nie mogę uzyskać dostępu do zewnętrz

Processing row 18: Massive herbarium merger rescues century-old plant collection
```

Brak błędu `FileNotFoundError`, uwierzytelnienie do Google Sheets zakończone sukcesem, skrypt pobrał zadania z arkusza i przeszedł do trybu roboczego.
