# vse-worker (Video SEO Engine Worker)

Autonomiczny worker w architekturze `media-dispatch` odpowiadający za kompleksowe przetwarzanie materiałów wideo: generowanie metadanych SEO, szkiców artykułów WordPress, synchronizację metadanych YouTube oraz przygotowanie propozycji i renderingu YouTube Shorts z wykorzystaniem API `video-seo-engine`.

---

## Architektura 4-stopniowego Pipeline'u

Worker implementuje 4-krokowy, zautomatyzowany przepływ produkcyjny:

```
[YouTube URL / Video ID]
       │
       ├─► Krok 1: POST /v1/generate
       │   └── Analiza transkrypcji (Claude) → SEO tytuły, opis, rozdziały, tagi, pełny artykuł WP
       │
       ├─► Krok 2: POST /v1/inject (post_status='draft')
       │   └── Wstrzyknięcie artykułu do WordPress jako SZKIC (draft)
       │
       ├─► Krok 3: YouTube Metadata Update (privacyStatus='unlisted')
       │   └── Wykonanie skryptu w kontenerze vse-api przez Google API Client
       │       Aktualizacja tytułu, opisu (z linkiem do WP i rozdziałami), tagów; zachowanie statusu 'unlisted'
       │
       └─► Krok 4: Shorts Extraction & Render
           ├── POST /v1/shorts/candidates — wyłonienie kandydatów (emocjonalnych i eksperckich)
           └── POST /v1/shorts/render — zgłoszenie zadań renderingu 9:16 z napisami SRT
```

---

## ⛔ Bezwzględne Zasady Operacyjne

1. **WordPress post_status:** ZAWSZE `draft` — żaden materiał nie może zostać opublikowany automatycznie bez autoryzacji.
2. **YouTube privacyStatus:** ZAWSZE `unlisted` — status wideo nie jest zmieniany na publiczny przez pipeline.
3. **Zarządzanie sekretami:** Brak hardkodowanych tokenów JWT i haseł. Tokeny pobierane są dynamicznie ze środowiska lub generowane w locie w kontenerze `vse-api`.

Szczegółowe wytyczne operacyjne i pułapki: [constitution.md](constitution.md).

---

## Zmienne Środowiskowe (Konfiguracja)

| Zmienna | Domyślna wartość | Opis |
|---------|------------------|------|
| `VSE_URL` / `VSE_API_URL` | `http://localhost:8085` | Adres bazowy instancji VSE API (port 8085!) |
| `VSE_JWT_TOKEN` | *brak (generowany w locie)* | Opcjonalny pre-generowany token Bearer JWT |
| `VSE_PORTAL_ID` | `2b047d7d-15a1-4d2f-8463-f89c2275bb73` | UUID docelowego portalu WordPress (domyślnie prawy.pl) |
| `VSE_CHANNEL_ID` | `UCoH2G9By4OX3kcLsc8lHgDw` | Identyfikator kanału YouTube w bazie VSE |
| `VSE_OUTPUT_DIR` | `/home/ubuntu/VSE/Shorts` | Ścieżka do zapisu wyrenderowanych plików Shortów |
| `VSE_SSH_KEY` / `SSH_KEY` | `C:\Users\tomas2\.ssh\oracle-crimson.key` | Ścieżka do klucza prywatnego SSH VPS |
| `VSE_VPS_HOST` / `VPS_HOST` | `ubuntu@147.224.162.100` | Host SSH do instancji VSE VPS |
| `VSE_LLM_PROVIDER` | `claude` | Dostawca LLM do generacji (na VPS dostępny Claude) |

---

## Użycie Programistyczne

### Przykładowy Task

```python
from agents.vse_worker.pipeline import VSEPipeline

pipeline = VSEPipeline()

task = {
    "video_url": "https://www.youtube.com/watch?v=EnclbKLEDAA",
    "video_id": "EnclbKLEDAA",
    "local_path": "/home/ubuntu/video-seo-engine/batch/input.mp4",  # opcjonalnie dla renderingu Shortów
    "portal_id": "2b047d7d-15a1-4d2f-8463-f89c2275bb73",         # opcjonalnie
    "channel_id": "UCoH2G9By4OX3kcLsc8lHgDw",                     # opcjonalnie
    "provider": "claude",                                         # opcjonalnie
    "steps": [1, 2, 3, 4],                                        # opcjonalnie — wybrane kroki
    "output_dir": "/home/ubuntu/VSE/Shorts"                       # opcjonalnie
}

result = pipeline.process(task)
print(result)
```

### Struktura Odpowiedzi

```json
{
  "status": "ok",
  "step1_generate": {
    "status": "ok",
    "status_code": 200,
    "schema_data": {
      "yt_title": "...",
      "seo_title": "...",
      "post_title": "...",
      "chapters": [...],
      "tags": [...]
    }
  },
  "step2_inject": {
    "status": "ok",
    "status_code": 200,
    "wp_post_id": 12345,
    "post_url": "https://prawy.pl/?p=12345"
  },
  "step3_yt_update": {
    "status": "ok",
    "title": "...",
    "privacyStatus": "unlisted"
  },
  "step4_shorts": {
    "status": "ok",
    "candidates": [...],
    "render_jobs": [
      {
        "job_id": "job_abc123",
        "title": "...",
        "start_sec": 12.0,
        "end_sec": 45.0,
        "status": "submitted"
      }
    ]
  }
}
```

---

## Interfejs Workera (`worker.py`)

Moduł `agents/vse-worker/worker.py` eksponuje ujednolicony interfejs agentów ekosystemu `media-dispatch`:

```python
import worker

# 1. Health check
status = worker.health_check()

# 2. Przetworzenie zadania
result = worker.process(task)

# 3. Odczyt ostatniego stanu
current_status = worker.get_status()
```

### CLI

```bash
# Sprawdzenie gotowości serwisu
python worker.py --health

# Odczyt statusu
python worker.py --status

# Uruchomienie pipeline dla filmu
python worker.py --video-url "https://www.youtube.com/watch?v=EnclbKLEDAA" --steps "1,2,3"

# Uruchomienie z pliku zadania
python worker.py --task task.json
```
