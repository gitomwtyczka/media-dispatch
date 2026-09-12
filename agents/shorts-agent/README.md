# shorts-agent

Dedykowany agent zarządzający formatem krótkim (**YouTube Shorts**) w architekturze `media-dispatch`.
Odpowiada za automatyczne wzbogacanie metadanych wideo przez **Short Machine API** w VSE (`POST /v1/shorts/describe`), aktualizację tytułów, opisów i tagów przez **YouTube Data API v3** oraz planowanie publikacji w czasie (**Scheduling Engine**).

---

## Co robi

1. **Short Machine Enrichment (`worker.py`)**:
   - Wywołuje produkcyjny endpoint VSE `POST /v1/shorts/describe` dla wskazanych wycinków czasowych filmów źródłowych.
   - Generuje zoptymalizowany pod algorytmy YouTube tytuł (front-loaded, max 45 znaków, bez `#Shorts`).
   - Generuje opis (150–350 znaków, bez klikalnych linków zewnętrznych) oraz do 5 precyzyjnych hashtagów.
   - Opcjonalnie przygotowuje pytanie polaryzujące pod przypięty komentarz (`pinned_comment`).
2. **Aktualizacja YouTube Data API**:
   - Pobiera aktualny stan filmu i snippetu (`categoryId`, `tags`).
   - Aktualizuje tytuł, opis z hashtagami oraz tagi wideo.
3. **Planowanie Publikacji (`scheduler.py`)**:
   - Zgodnie ze standardem YouTube Data API ustawia `privacyStatus: private` oraz `publishAt` (ISO 8601 UTC).
   - Zapewnia mechanizm fallback w przypadku problemów z harmonogramem daty.

---

## Zmienne Środowiskowe (Environment Variables)

Wszystkie sekrety i parametry połączeniowe są w pełni konfigurowalne przez zmienne środowiskowe:

| Zmienna | Domyślna wartość | Opis |
|---------|------------------|------|
| `VSE_URL` | `http://localhost:8085` | Bazowy adres URL API VSE (np. `https://vse.impresjapr.pl` lub `http://localhost:8085`) |
| `VSE_API_HOST` | `localhost:8085` | Alternatywny host VSE API |
| `SHORTS_PORTAL_ID` | `2b047d7d-15a1-4d2f-8463-f89c2275bb73` | UUID portalu (np. prawy.pl) przekazywany do VSE |
| `VSE_JWT` | *(brak)* | Opcjonalny pre-generowany token JWT dla VSE API. W razie braku, worker pobiera go automatycznie przez Docker/SSH |
| `YOUTUBE_OAUTH_TOKEN` | *(brak)* | Opcjonalny token OAuth2 dla YouTube Data API. W razie braku, worker pobiera go bezpośrednio z bazy danych VSE |
| `SSH_HOST` | `ubuntu@147.224.162.100` | Host SSH do serwera VPS z bazą VSE |
| `SSH_KEY_PATH` | `~/.ssh/oracle-crimson.key` | Ścieżka do klucza prywatnego SSH |

---

## Jak uruchomić

### 1. Z poziomu Pythona (Programistycznie)

```python
from agents.shorts_agent.worker import health_check, process, get_status
from agents.shorts_agent.scheduler import schedule_short

# 1. Sprawdzenie stanu połączeń
health = health_check()
print("Health status:", health)

# 2. Przetworzenie zadania z listą shortów
task = {
    "shorts": [
        {
            "short_id": "slA15REfjpU",
            "source_youtube_id": "77ZwKDuOQ1M",
            "start_sec": 723.0,
            "end_sec": 773.5,
            "name": "Polska_konstytucja"
        }
    ],
    "portal_id": "2b047d7d-15a1-4d2f-8463-f89c2275bb73",
    "channel_name": "@PrawyTV",
    "provider": "claude"
}

result = process(task)
print("Wynik przetwarzania:", result)

# 3. Zaplanowanie publikacji shorta
schedule_res = schedule_short(
    short_id="slA15REfjpU",
    publish_at_utc="2026-09-15T07:00:00Z",
    title="Konstytucja z 1997 roku jest pełna wad!",
    description="Czy Polska potrzebuje nowej ustawy zasadniczej?"
)
print("Harmonogram:", schedule_res)
```

### 2. Z poziomu CLI (Linia poleceń)

```bash
# Diagnostyka i test tokenów
python agents/shorts-agent/worker.py --health

# Przetwarzanie zadania z pliku JSON
python agents/shorts-agent/worker.py --task-file task_example.json

# Pobranie ostatniego stanu workera
python agents/shorts-agent/worker.py --status

# Zaplanowanie publikacji konkretnego shorta
python agents/shorts-agent/scheduler.py --video-id slA15REfjpU --publish-at "2026-09-15T07:00:00Z"

# Zaplanowanie batcha z pliku harmonogramu
python agents/shorts-agent/scheduler.py --batch-file schedule_batch.json
```

---

## Format Zadania (`task` dict)

Struktura parametru wejściowego dla `process(task)`:

```json
{
  "shorts": [
    {
      "short_id": "slA15REfjpU",
      "source_youtube_id": "77ZwKDuOQ1M",
      "start_sec": 723.0,
      "end_sec": 773.5,
      "name": "Polska_konstytucja"
    },
    {
      "short_id": "8nbA6YSZAVQ",
      "source_youtube_id": "77ZwKDuOQ1M",
      "start_sec": 481.0,
      "end_sec": 528.5,
      "name": "Organizacje_Twoj_glos"
    }
  ],
  "portal_id": "2b047d7d-15a1-4d2f-8463-f89c2275bb73",
  "channel_name": "@PrawyTV",
  "provider": "claude",
  "insert_pinned_comment": false
}
```

---

## Krytyczne Reguły Algorytmiczne i Pułapki

- **Brak `#Shorts` w tytule**: YouTube od 2024 automatycznie klasyfikuje format 9:16 poniżej 60s jako Short.
- **Zakaz linków URL w opisach**: Linki są nieklikalne na urządzeniach mobilnych i ucinają zasięgi.
- **Długość tytułu**: Tytuł powinien mieć maksymalnie **45 znaków** (front-loaded), aby nie był obcięty w interfejsie mobilnym YouTube.
- **Zasada planowania `publishAt`**: W YouTube Data API zaplanowanie `publishAt` wymaga bezwzględnie ustawienia `privacyStatus: private`.
