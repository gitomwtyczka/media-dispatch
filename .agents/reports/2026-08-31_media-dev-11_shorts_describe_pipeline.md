# Raport: Przygotowanie integracji i skryptu dla 8 Shortów (POST /v1/shorts/describe)

**Data:** 2026-08-31 23:10  
**Autor:** `media-dev-11`  
**Workspace:** `media-dispatch`  
**Status:** Skrypt wdrożeniowy przygotowany i skomitowany do repozytorium  

---

## 1. Zakres prac

1. Zapoznano się z dokumentacją pre-flight:
   - `.agents/knowledge/vse-worker-constitution.md` (architektura, pułapki VSE, auth JWT, YouTube OAuth przez `_build_credentials`)
   - `docs/vse-integration-answers.md` (kontrakt `/v1/shorts/describe`, struktura wejścia/wyjścia)
   - `docs/shorts-publication-guide.md` (standardy publikacji YouTube 2025/2026 — max 45 zn tytułu, brak `#Shorts` w tytule, brak linków URL, pinned comment, 3-5 hashtagów).

2. Przygotowano pełny skrypt produkcyjny: `agents/vse-worker/scripts/process_shorts_describe.py`.
   - Generuje poprawny token JWT przez `jose.jwt.encode` z `JWT_SECRET_KEY`.
   - Pobiera i odświeża aktywne tokeny YouTube z bazy danych VSE (`YouTubeChannel` -> `_build_credentials.refresh()`).
   - Wywołuje `POST /v1/shorts/describe` dla 8 wskazanych shortów:
     1. `ioObSLpRGc4` (01.09 07:00 — PRIORYTET #1)
     2. `FtQNSzHtQ0s` (01.09 12:00 — PRIORYTET #2)
     3. `9tjEXGE5sXg` (01.09 18:00 — PRIORYTET #3)
     4. `mw6A9CZ6DuM` (private)
     5. `mTyr64ygkJU` (private)
     6. `8nbA6YSZAVQ` (private)
     7. `slA15REfjpU` (private)
     8. `lX2vvs8E-AY` (private)
   - Aktualizuje tytuł i opis z hashtagami przez YouTube Data API v3 (`videos().update`), zachowując istniejący status publikacji (`privacyStatus` / `publishAt`).
   - Dodaje `pinned_comment` przez `commentThreads().insert` jako komentarz właściciela kanału.
   - Zapisuje wyniki do `/tmp/shorts_described.json`.

---

## 2. Stan wykonania i uruchomienie

- Plik skryptu został skomitowany do gałęzi `main`: `agents/vse-worker/scripts/process_shorts_describe.py` (Commit: `ae7a008de88109740552328246c72b04d5a3d1b9`).
- Lokalny runner w subagencie napotkał timeout uprawnień interaktywnych GUI przy bezpośrednim wywołaniu SSH/SCP (`run_command` permission timeout).
- Instrukcja uruchomienia bezpośrednio na VPS:
  ```bash
  ssh -i C:\Users\tomas2\.ssh\oracle-crimson.key -o StrictHostKeyChecking=no ubuntu@147.224.162.100
  docker cp /home/ubuntu/video-seo-engine/agents/vse-worker/scripts/process_shorts_describe.py vse-api:/app/process_shorts_describe.py 2>/dev/null || docker exec -w /app vse-api curl -s https://raw.githubusercontent.com/gitomwtyczka/media-dispatch/main/agents/vse-worker/scripts/process_shorts_describe.py -o /app/process_shorts_describe.py
  docker exec -w /app vse-api python3 /app/process_shorts_describe.py
  ```

---
*media-dev-11 | media-dispatch | 31.08.2026*
