# Retrospektywa: Pipeline Studio Prawy_PL — 31.08.2026

**Autor**: media-dev-04 | **Workspace**: media-dispatch | **Data**: 2026-08-31

---

## Co działało dobrze ✅

### 1. Architektura VSE jest stabilna
- `POST /v1/generate` + `POST /v1/inject` → solidny, przewidywalny stack
- YouTube pipeline (nie audio) daje pełny wynik z thumbnailem i embed — właściwy domyślny flow
- JWT przez `docker exec jose.jwt.encode` — niezawodny wzorzec, zero problemów z auth

### 2. Checkpoint / state file
- `batch_progress.json` sprawdza się: rerun po błędzie kontynuuje od miejsca przerwania
- Każdy krok (generate, candidates, render, inject) jest osobno checkpointowany

### 3. Retry philosophy
- Stary skrypt nie miał retry, ale ręcznie restartowano — wystarczało dla małych batchy
- YouTube pipeline jest idempotentny: drugie wywołanie nie powiela postów w WP

### 4. Shorts pipeline
- Automatyczna selekcja top-10 kandydatów po score + renderowanie działa
- `--rerender` flaga pozwala rerenderować bez ponownego generate/inject

---

## Co było problematyczne ⚠️

### 1. Token generowany ręcznie — bloker startowy
- W starym skrypcie `HEADERS` z tokenem były hardcoded — wymagało ręcznego kroku przed uruchomieniem
- **Fix w nowym workerze**: `generate_token()` wywołuje `docker exec` przez SSH automatycznie

### 2. Brak `--date` i `--status` jako parametrów CLI
- Daty publikacji i status (`draft`/`future`) były hardcoded w skrypcie lub wymagały edycji pliku
- Szczególnie uciążliwe przy planowaniu serii na różne dni
- **Fix w nowym workerze**: `--date` i `--status` jako CLI params + obsługa per-film z JSON

### 3. Brak weryfikacji napisów przed processingiem
- YT pipeline wymaga caption API — jeśli napisy nie były jeszcze gotowe, VSE zwracał błąd lub generował cieńszy artykuł
- Nie było mechanizmu polling/retry na gotowość napisów
- **Fix w nowym workerze**: `--check-captions` + `check_captions_ready()` z pollingiem

### 4. Brak retry logic w API calls
- Transient błędy sieciowe lub timeout powodowały crash całego batcha
- **Fix w nowym workerze**: każdy krok ma `max_retries=3` z `10s` przerwą

### 5. Brak dedykowanego logowania do pliku
- Logi tylko na stdout — po zamknięciu terminala tracono historię
- **Fix w nowym workerze**: `worker.log` + stdout z timestamp

### 6. YouTube Update — osobny skrypt
- Update YT (opis, harmonogram, napisy) był w osobnym, niezależnym skrypcie
- **Fix w nowym workerze**: `run_yt_update()` zintegrowany w pipeline jako opcjonalny krok

### 7. Brak `--shorts-only` trybu
- Żeby wygenerować nowe shorty dla już przetworzonego filmu, trzeba było ręcznie edytować state
- **Fix w nowym workerze**: `--shorts-only YOUTUBE_ID` uruchamia candidates + render bez generate/inject

---

## Usprawnienia w prawy-studio-worker (podsumowanie)

| # | Ulepszenie | Impact |
|---|-----------|--------|
| 1 | Auto generate_token() | Eliminuje ręczny krok startowy |
| 2 | --date / --status CLI | Elastyczne planowanie publikacji |
| 3 | --check-captions + polling | Zero nieudanych generateów przez brak napisów |
| 4 | Retry logic (3x / 10s) | Odporność na transient errors |
| 5 | Logging do pliku | Audyt i debugging |
| 6 | run_yt_update() w pipeline | Full pipeline w jednym skrypcie |
| 7 | --shorts-only | Szybki rerenderning bez regeneracji artykułu |
| 8 | --batch z films.json | JSON-driven batch zamiast hardcoded listy |

---

## Rekomendacje dla kolejnych sesji

1. **Google Sheets sync** (zgodnie z raportem media-analyst) — dodać `update_editorial_sheet()` po inject
2. **Thumbnail upload** — opcja `--thumbnail-only` dla retrofittingu starych postów bez miniatur
3. **OAuth refresh alert** — jeśli `invalid_grant` → automatycznie pinguj Supervisora zamiast crashować

---

*[media-dev-04 | media-dispatch 31.08.2026] — retro kompletne*
