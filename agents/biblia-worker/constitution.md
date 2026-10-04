# Biblia Worker - Konstytucja

## Pre-flight checklist
1. Sprawdź czy token JWT można wygenerować poprawnie (testuj `get_jwt_token()`)
2. Zweryfikuj dostępność VPS po SSH.
3. Zweryfikuj daty w strefach czasowych (Local vs GMT vs ISO).
4. Przeczytaj Znane Pułapki poniżej przed modyfikacją kodu.

## Znane Miny (Pułapki)
1. **WP Status Ignorowany:** Endpoint `/v1/inject` zawsze tworzy draft. Zawsze trzeba zrobić manualny `wp post update` po fakcie za pomocą WP-CLI.
2. **PORTAL_ID Alias:** Używaj pełnego UUID (`2b047d7d-15a1-4d2f-8463-f89c2275bb73`), alias `prawy` nie działa w niektórych starszych endpointach.
3. **PUB_TYPE:** Musi być `full_analysis`. Ustawienie `film` rzuca 422.
4. **YT Channel:** Prawy TV to ID `UCNXh5eIlMVxnUBpTMKUp4CA`. Nie myl ze "Studio Prawy_PL".
5. **LLM Provider:** Używaj `claude`. Gemini na VPS nie ma przypisanego klucza.
6. **SSH Comands:** Wykonuj polecenia SSH pojedynczo za pomocą Pythona (`subprocess`). Nie łącz w skrypcie shellowym operatorem `&&`.
7. **SCP Pathing:** Używaj pełnych ścieżek Windows (np. `C:\\Users\\...\\oracle-crimson.key`).

## Flow (5 kroków)
1. JWT Token (pobranie JWT_SECRET z VPS + podpis JWT)
2. VSE Generate (`/v1/generate`)
3. VSE Inject (`/v1/inject`) -> Zawsze zwraca Draft!
4. WP-CLI Post-processing (Status, Data, Kategoria `prawy-biblijny`, Meta Youtube URL, Flush Cache)
5. YouTube Update (`/v1/youtube/publish-description`)

## Credentials Inventory
- Klucz SSH: `C:\\Users\\tomas2\\.ssh\\oracle-crimson.key` (ubuntu@147.224.162.100)
- VSE / WP: Dostęp przez dockera na VPS (`vse-api`, `prawy-wordpress`)
- Baza kodów autoryzacyjnych na sztywno w `config.py`.

## Anti-patterns
- Nigdy nie sprawdzaj kodu źródłowego VSE z poziomu workera, aby zgadywać endpointy. Wszystko jest w Konstytucji.
- Nie używaj `create_access_token` - używaj bezpośrednio `pyjwt.encode`.
- Nie łącz komend w wielkie skrypty bash - trudniej zdebugować jeśli coś się zatnie (np. zła podstrefa).


## ZASADY ZERO-PYTAŃ (Nowe)
1. **Zero eksploracji kodu** (grep/sed zabronione) — uruchamiasz `python scripts/run_batch.py batch.json`.
2. **Obsługa błędów**:
    | Błąd | Akcja | Czy pytać usera? |
    |---|---|---|
    | 4xx (inne) | fail-fast na rekordzie, continue | NIE |
    | invalid_grant | STOP batcha, wpis do results | TAK |
    | brak MP4 | fail-fast na rekordzie, gdy brak transkryptu | TAK (jeśli brak) |
3. **Transcript Guard**: Jeśli YT nie ma transkryptu (wykryta fraza 'brak transkryptu'), agent pobiera fallback MP4 (zazwyczaj AMEEncodingLog.txt UTF-16LE wskazuje ścieżkę), wyciąga MP3 i pinguje /v1/audio/generate.
4. **Źródło MP4**: AMEEncodingLog.txt (konieczne kodowanie UTF-16LE).
5. **Idempotencja**: Przed wstrzyknięciem do WP, worker zawsze odpytuje /v1/check (po video_id). Jeśli istnieje, pomija krok Inject.
6. **Reguła publikowania (AGENTS.md)**: Domyślnie 'draft' (WP) i 'unlisted' (YT). Zmiana tylko na wyraźne żądanie (publish_now=true) lub data w przeszłości/przyszłości jawnie zadana.
7. **Zakończenie pracy**: Worker zawsze generuje plik `results.json` i po jego analizie pisze Raport (do repo lokalnego i sonic-void).

8. **Bezpieczeństwo**: Wszystkie operacje (batch i patch-meta) uruchamiają się jako `dry-run`. Do zapisu produkcyjnego wymagana jest flaga `--execute`.
