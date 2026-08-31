# prawy-studio-worker

Dedykowany worker dla kanału **Studio Prawy_PL** w architekturze `media-dispatch`.
Obsługuje pełny pipeline VSE: generate SEO → inject WordPress → YouTube update → Shorts.

## Co robi

1. **Generuje token JWT** automatycznie przez SSH (`docker exec vse-api`)
2. **Weryfikuje gotowość napisów** przed processingiem (YouTube captions polling)
3. **Uruchamia pipeline VSE** per film:
   - `POST /v1/generate` → SEO metadata + artykuł WP
   - `POST /v1/inject` → WordPress draft/future z miniaturą i Rank Math
   - `PUT /v1/youtube/publish-description` → update opisu YT
   - `POST /v1/shorts/candidates` + `POST /v1/shorts/render` → shorty 9:16
4. **Checkpointuje stan** w `batch_progress.json` — rerun kontynuuje od miejsca błędu
5. **Loguje** do `worker.log` + stdout z timestamp

## Konfiguracja

Stałe konfiguracyjne na górze `worker.py`:

| Stała | Wartość | Opis |
|-------|---------|------|
| `VSE_URL` | `https://vse.impresjapr.pl` | URL publiczny VSE |
| `PORTAL_ID` | `2b047d7d-15a1-4d2f-8463-f89c2275bb73` | UUID prawy.pl |
| `YT_CHANNEL_ID` | `UCoH2G9By4OX3kcLsc8lHgDw` | Studio Prawy_PL channel |
| `SSH_HOST` | `ubuntu@147.224.162.100` | VPS |
| `SSH_KEY` | `C:\Users\tomas2\.ssh\oracle-crimson.key` | Klucz SSH |
| `LOCAL_VIDEO_DIR` | `C:\Users\tomas2\Videos\Prawy` | Lokalne wideo |
| `OUTPUT_DIR` | `C:\VSE\Shorts` | Output shortów |
| `STATE_FILE` | `batch_progress.json` | Checkpoint |

Alternatywnie: skopiuj `config.example.json` → `config.json` i nadpisz w kodzie.

## Uruchamianie

### Przetwórz jeden film
```bash
python worker.py --single YOUTUBE_ID
python worker.py --single YOUTUBE_ID --date 2026-09-01 --status future
python worker.py --single YOUTUBE_ID --status draft
```

### Batch z pliku JSON
```bash
# Skopiuj template:
cp films_template.json films.json
# Edytuj films.json, następnie:
python worker.py --batch films.json
```

### Lista filmów i ich status
```bash
python worker.py --list
```

### Tylko shorty (bez regeneracji artykułu)
```bash
python worker.py --shorts-only YOUTUBE_ID
```

### Sprawdź gotowość napisów
```bash
python worker.py --check-captions YOUTUBE_ID
```

### Reset checkpointu
```bash
python worker.py --reset YOUTUBE_ID
```

## Parametry CLI

| Parametr | Opis |
|----------|------|
| `--single YOUTUBE_ID` | Przetwórz jeden film przez pełny pipeline |
| `--batch films.json` | Przetwórz filmy z pliku JSON |
| `--list` | Wyświetl listę filmów z checkpointu i ich status |
| `--shorts-only YOUTUBE_ID` | Generuj shorty bez regeneracji artykułu WP |
| `--check-captions YOUTUBE_ID` | Sprawdź/poczekaj na gotowość napisów |
| `--reset YOUTUBE_ID` | Usuń checkpoint dla danego filmu |
| `--date YYYY-MM-DD` | Data publikacji (domyślnie: jutro) |
| `--status draft\|future\|publish` | Status postu WP (domyślnie: `future`) |

## Format films.json

```json
[
  {
    "youtube_id": "abc123xyz",
    "title": "Tytuł roboczy",
    "local_path": "C:\\Users\\tomas2\\Videos\\Prawy\\film.mp4",
    "publish_date": "2026-09-01",
    "post_status": "future"
  }
]
```

## Pipeline — diagram

```
[youtube_id]
    │
    ├─► generate_token()         # JWT przez SSH+docker exec
    │
    ├─► check_captions_ready()   # polling gotowości napisów YT
    │
    ├─► run_generate()           # POST /v1/generate → schema_data
    │       └── checkpoint: schema_data
    │
    ├─► run_inject()             # POST /v1/inject → wp_post_id, wp_url
    │       └── checkpoint: wp_post_id, wp_url
    │
    ├─► run_yt_update()          # PUT /v1/youtube/publish-description
    │       └── checkpoint: yt_updated
    │
    ├─► run_shorts_candidates()  # POST /v1/shorts/candidates
    │       └── checkpoint: candidates
    │
    └─► run_shorts_render()      # POST /v1/shorts/render (top 10)
            └── checkpoint: render_jobs
```

## Wymagania

- Python 3.9+
- `requests` (`pip install requests`)
- Dostęp SSH do VPS: `ubuntu@147.224.162.100` z kluczem `oracle-crimson.key`
- Działający VSE na VPS z kontenerem `vse-api`

## Znane pułapki

Szczegółowa lista w: [`.agents/knowledge/vse-worker-constitution.md`](../../.agents/knowledge/vse-worker-constitution.md)

Kluczowe:
- `llm_provider` musi być `"claude"` (nie `"gemini"`)
- `publication_type` musi być `"full_analysis"` (nie `"film"`)
- `portal_id` musi być UUID (nie string `"prawy"`)
- Jeśli YT zwraca `invalid_grant` → OAuth wygasł, zgłoś do Supervisora

## Status

- **MVP v1.0** — zaimplementowany 31.08.2026 przez media-dev-04
