# Post-mortem analiza sesji Biblia Pipeline 16.09.2026

**Od:** Supervisor 01 | sonic-void
**Callsign:** [post-mortem-analyst | sonic-void 16.09.2026]

## 1. CO ZADZIALAŁO (single source of truth)
Ścieżka, która z powodzeniem utworzyła wpisy na prawy.pl (5/5 sukces):
- **VSE Generate (`/v1/generate`)**:
  - `video_url`: `https://www.youtube.com/watch?v={yt_id}` (Należy używać URL YouTube, nie pliku audio, aby generował się thumbnail i embed)
  - `portal_id`: `"2b047d7d-15a1-4d2f-8463-f89c2275bb73"` (Używamy bezwzględnie UUID, alias 'prawy' powodował błędy)
  - `llm_provider`: `"claude"` (Nie "gemini", gdyż brakuje klucza na VPS)
  - `lang`: `"pl"`
  - `publication_type`: `"full_analysis"`
- **VSE Inject (`/v1/inject`)**:
  - Przekazujemy `schema_data` z `/v1/generate`
  - `publish_date`: Odpowiednia data (np. `"2026-09-16T00:00:01+02:00"`)
  - `status`: `"future"` (dla zaplanowanych) lub `"publish"`
  - `portal_id`: `"2b047d7d-15a1-4d2f-8463-f89c2275bb73"`
- **Autoryzacja VSE (JWT)**:
  - Header: `Authorization: Bearer {token}`
  - Generowanie: Algorytm HS256, `sub="4b97ab0c-98ee-46c6-9be8-d86adc4cb38a"`, `email="tobroz@gmail.com"`, `JWT_SECRET` pobierany z `.env` na serwerze.
- **Wyniki (WP Post IDs)**:
  - `AMd9euz4dvM` → wp=126371 (2026-09-15)
  - `vNoDWfjXHIU` → wp=126376 (2026-09-16)
  - `2IB0AXXhagk` → wp=126381 (2026-09-17)
  - `-z8X2PEuW34` → wp=126386 (2026-09-18)
  - `0rGHXiSVM-4` → wp=126391 (2026-09-19)

## 2. CO NIE ZADZIAŁAŁO I DLACZEGO
- **YouTube 403 Forbidden**: Raw `access_token` wyciągnięty wprost z bazy danych wygasa po około godzinie. Użycie go w requestach (np. `requests.put` czy API klienta YouTube) rzucało błędem autoryzacji 403 Forbidden.
- **Worker anti-pattern**: Zamiast skupić się na wykonaniu przygotowanego skryptu (uruchomienie go w odpowiednim kontenerze i zebranie wyników), workerzy zaczęli zagłębiać się w kod (np. parsowanie/czytanie kodu VSE za pomocą grep/sed). Przez to tracili kontekst i nie byli w stanie dokończyć właściwego prostego zadania wykonania kodu i zaktualizowania API.
- **Błędne nazwy kolumn modeli**: Próba użycia `ch.channel_id` czy `ch.client_id` zamiast prawidłowego `ch.youtube_channel_id` rzucała `AttributeError`.

## 3. YOUTUBE — OTWARTA KWESTIA
- **Co próbowano**: Próbowano aktualizować opisy i status używając bezpośrednio `requests.put` z raw tokenem, a potem budując poświadczenia wewn. skryptami. Worker podjął próbę wylistowania playlisty za pomocą _build_credentials, ale finalna aktualizacja się nie powiodła.
- **Co powinno działać**: Najlepiej użyć endpointu VSE `POST /v1/youtube/publish-description`, autoryzując się za pomocą VSE JWT (z konta tobroz@gmail.com). Endpoint automatycznie obsłuży uwierzytelnienie w YouTube API za pomocą mechanizmów VSE, dbając o tokeny (odświeżanie) na podstawie zintegrowanych sesji. Alternatywą jest poprawne użycie `api.core.youtube_publish._build_credentials` do odświeżenia tokena wprost z wewnątrz kontenera `vse-api`.
- **Co jeszcze trzeba zrobić**: Wszystkie 5 filmów (np. AMd9euz4dvM, vNoDWfjXHIU, itd.) jest nadal w stanie **Niepubliczny (unlisted)** na YouTube. Należy odświeżyć ich opis i ustawić widoczność na Publiczną / zaplanować na konkretne daty.

## 4. DISPATCH TEMPLATE NA PRZYSZŁOŚĆ
**Lokalizacja pipeline'ów**: Repozytorium `media-dispatch`, ścieżka `agents/vse-worker/scripts/`.
- `biblia_full_pipeline.py`: Prawidłowy pełny flow (audio -> transkrypcja -> captions -> SEO yt -> WP). Używać dla nowych filmów.
- `biblia_backlog_pipeline.py`: Poprawiona wersja skryptu obsługującego VSE JWT i `_build_credentials`. Wykorzystuje UUID dla portalu i prawidłowy `llm_provider`. Z niego należy korzystać dla aktualizacji zaległości.

**Szablon Dispatchu dla agentów biblijnych**:
```markdown
# DISPATCH — Biblia Pipeline

**Zasada:** TYLKO WYKONAJ ZADANE KROKI, NIE CZYTAJ I NIE EKSPLORUJ KODU ZRODŁOWEGO VSE. Masz gotowy skrypt/polecenia.

Skrypt do uruchomienia to `biblia_full_pipeline.py` (lub w razie backlogu `biblia_backlog_pipeline.py`), dostępny w repozytorium `media-dispatch` pod `agents/vse-worker/scripts/`.
1. Zapisz skrypt do `/tmp/`.
2. Prześlij przez SCP do kontenera/serwera.
3. Wykonaj.

## ⚠️ ZNANE PUŁAPKI biblia-worker (przeczytaj ZANIM zaczniesz)
1. SCP na Windows: NIGDY nie używaj `~` w ścieżce lokalnej. Zawsze podawaj pełną ścieżkę (np. `C:\Users\tomas2\.ssh\...`).
2. Skrypty VSE z zależnościami (np. requests, jose, google-api-python-client) uruchamiaj ZAWSZE wewnątrz kontenera: `docker exec vse-api python3 /app/<skrypt.py>`.
3. Wywoływanie poleceń SSH w PowerShellu: Nie łącz komend przy użyciu `&&`. Wykonuj krok po kroku.
4. Token YT (`access_token`) wygasa! Nie wklejaj go jako statyczny string, zawsze korzystaj z VSE API `/v1/youtube/publish-description` (używając VSE JWT) lub wykorzystaj wbudowany moduł VSE `api.core.youtube_publish._build_credentials`.
5. Portal ID to ZAWSZE UUID (`2b047d7d-15a1-4d2f-8463-f89c2275bb73`), nie używaj aliasów stringowych (np. "prawy"). LLM Provider to `claude`.
```

## 5. ZNANE PUŁAPKI (gotowy blok do wklejenia w dispatche)
```markdown
## ⚠️ ZNANE PUŁAPKI biblia-worker
1. **SCP Windows**: NIGDY `~` w lokalnej ścieżce. Zawsze pełne ścieżki Windows.
2. **Uruchamianie**: Skrypt uruchamiaj przez `docker exec vse-api python3 /app/<skrypt.py>`, aby zagwarantować obecność zależności.
3. **SSH w PS**: Jeden krok na raz przez SSH — nie łącz komend przez `&&`.
4. **Tokeny YouTube**: Raw `access_token` wygasa po 1h. Używaj VSE endpointu `/v1/youtube/publish-description` z JWT (VSE ogarnie YT) lub metody `_build_credentials()` z wnętrza kontenera.
5. **Parametry VSE**: `portal_id` to UUID (`2b047d7d-15a1-4d2f-8463-f89c2275bb73`), a `llm_provider` to `claude` (brak gemini na VPS).
```
