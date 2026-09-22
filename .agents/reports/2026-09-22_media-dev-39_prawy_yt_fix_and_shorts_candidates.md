# Raport: Prawy YT Fix & Shorts Candidates Diagnostic Pipeline

- **Callsign:** `media-dev-39`
- **Data:** 22.09.2026
- **Workspace:** `media-dispatch` (branch `main`)
- **Status:** Done / Gotowe do uruchomienia przez Supervisora

---

## 1. Zrealizowane zadania i commity

1. **`agents/vse-worker/scripts/prawy_yt_fix_21_09_2026.py`** (commit `8a76927b`)
   - Samodzielny pipeline naprawiający `title` i `description` YouTube API v3 dla 6 filmów z 21.09.2026:
     - `Hsxu5L-27sU` (Płużański Kołakowska Jankowski, WP #126808)
     - `vZAm46QIq84` (Płużański Kołakowska Danuta, WP #126813)
     - `-9y8AGJSNFs` (Klimczak Woś 1, WP #126818)
     - `lJLC8rqnlCs` (Oskar Szafarowicz trybunał, WP #126823)
     - `PiwRUriZngc` (Oskar Szafarowicz przegląd, WP #126828)
     - `J0Z1xMSqkls` (Płużański Komuda Rozbiory 2, WP #126833)
   - Uwzględnienie wszystkich 8 pułapek:
     - Pozyskanie JWT przez `jose.jwt.encode` w kontenerze `vse-api`.
     - Wywołanie na żywo `POST /v1/generate` w celu pozyskania pola `youtube_description_body` (które nie istnieje w bazie DB).
     - Obcięcie `title` do max 100 znaków i wstrzyknięcie pełnego snippetu (`title`, `description`, `categoryId`) przez pobranie `videos().list(part='snippet')` przed `videos().update()`.
     - Skrypt kontenera tworzony jako lista linii `'\n'.join()` bez zagnieżdżonych f-stringów.
     - Bezpieczne rzutowanie `chapter.get('time')` na string w fallbacku opisu.
     - Wyniki zapisywane do `C:\Users\tomas2\.gemini\antigravity\brain\yt_fix_results.json`.
     - Brak znaków emoji w `print()` dla zgodności z `PYTHONUTF8=1`.

2. **`agents/vse-worker/scripts/prawy_shorts_candidates_21_09_2026.py`** (commit `20f4b9b9`)
   - Pipeline i skrypt diagnostyczny OpenAPI dla modułu Shorts:
     - Automatyczne pobranie `openapi.json` z VSE API (zarówno przez SSH z `http://localhost:8085/openapi.json`, jak i przez HTTP GET z `https://vse.impresjapr.pl/openapi.json`).
     - Ekstrakcja definicji ścieżek `/v1/shorts/*` oraz odwołań do modeli Pydantic w `components.schemas`.
     - Zapis wyekstrahowanego schematu do `C:\Users\tomas2\.gemini\antigravity\brain\shorts_openapi_schema.json`.
     - Wykonanie zapytań `POST /v1/shorts/candidates` dla 6 filmów z parametrami zweryfikowanymi w `pipeline.py` (`count_emotional=5`, `count_professional=5`, `provider="claude"`, `portal_id=PORTAL_ID`).
     - Zapis wyników, statusów oraz ew. błędów walidacji 422 do `C:\Users\tomas2\.gemini\antigravity\brain\shorts_candidates_results.json`.
     - Brak emoji w `print()`.

3. **`.agents/knowledge/vse-worker-constitution.md`** (commit `bc01353a`)
   - Sekcja 3: oznaczenie `/v1/youtube/publish-description` jako ⚠️ BROKEN dla kanałów Prawy.
   - Sekcja 11: całkowite zastąpienie starego wzorca `/v1/shorts/generate` (422) nową architekturą `candidates → render` oraz dodanie referencji do `POST /v1/shorts/describe` po uploadzie.
   - Sekcja 14: zastąpienie metody czytania z DB wzorcem Biblia / live response (`youtube_description_body` z `POST /v1/generate`, pełny snippet z `title`, `videos().list()` przed `update()`).
   - Sekcja 17 (NOWA): jednoznaczne zdefiniowanie kanałów aktywnych (`Studio Prawy_PL`: `UCoH2G9By4OX3kcLsc8lHgDw` i `Prawy TV`: `UCNXh5eIlMVxnUBpTMKUp4CA`) oraz kanałów out of scope (`Tomasz Brzozowski`, `VeriNarrMundo`).
   - Sekcja 8: dodanie pułapek 19-21.

4. **Aktualizacje stanu projektu**
   - `heartbeat.json` (commit `519df9aa`): status working, zadania zdefiniowane.
   - `.agents/tasks/current.md` (commit `0adac629`): zaktualizowane sekcje Zamknięte / W toku / Następne.

---

## 2. Raport techniczny i status BLOKERA (Shorts Candidates)

- **Status schematu:** W kodzie produkcyjnym `agents/vse-worker/pipeline.py` (commit `8226af8e`) odnaleziono działający wzorzec:
  - `POST /v1/shorts/candidates` z payloadem:
    ```json
    {
      "youtube_id": "...",
      "youtube_url": "...",
      "count_emotional": 5,
      "count_professional": 5,
      "provider": "claude",
      "portal_id": "2b047d7d-15a1-4d2f-8463-f89c2275bb73"
    }
    ```
  - `POST /v1/shorts/render` z payloadem per candidate:
    ```json
    {
      "youtube_id": "...",
      "youtube_url": "...",
      "local_path": "...",
      "start_sec": 0.0,
      "end_sec": 0.0,
      "candidate_data": { ... },
      "render_format": "9:16",
      "subtitles": "srt",
      "output_dir": "C:\\VSE\\Shorts",
      "portal_id": "..."
    }
    ```
- **Zabezpieczenie diagnostyczne:** Skrypt `prawy_shorts_candidates_21_09_2026.py` nie zakłada schematu na ślepo — przy uruchomieniu najpierw pobiera `openapi.json` przez SSH/HTTP, weryfikuje specyfikację FastAPI i zapisuje ją do pliku. Jeśli serwer zwróci błąd walidacji 422, szczegóły brakujących pól zostaną natychmiast wyeksportowane do logu i JSON-a.
- **Brak lokalnego uruchamiania:** Zgodnie z wytycznymi („Worker pisze skrypty Python i pushuje do GitHub MCP. NIE uruchamiasz run_command”), oba skrypty zostały wypchnięte do repozytorium GitHub i są gotowe do bezpośredniego uruchomienia przez Supervisora.
