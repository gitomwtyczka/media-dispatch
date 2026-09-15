# shorts-agent — Konstytucja

> Plik dla agentów AI które wywołują shorts-agent.  
> Ostatnia aktualizacja: 12.09.2026 | media-dev-A

---

## 1. Tożsamość

| Pole | Wartość |
|------|--------|
| **Callsign** | `shorts-agent` |
| **Warstwa** | Production / Distribution (Warstwa 3/4) |
| **Stack** | Python 3.10+ · requests · YouTube Data API v3 · VSE Short Machine API |
| **Środowisko** | VPS / Docker (`vse-api`) / Dev PC |
| **Skrypty** | `agents/shorts-agent/worker.py`, `agents/shorts-agent/scheduler.py` |

---

## 2. Jak wywołać

### Składnia bazowa (Programistyczna)

```python
from agents.shorts_agent.worker import health_check, process, get_status
from agents.shorts_agent.scheduler import schedule_short, schedule_shorts_batch

# 1. Health check
status = health_check()

# 2. Przetworzenie zadania
task = {
    "shorts": [
        {
            "short_id": "<YT_SHORT_ID>",
            "source_youtube_id": "<YT_SOURCE_VIDEO_ID>",
            "start_sec": 0.0,
            "end_sec": 60.0,
            "name": "<NAZWA_SHORTA>"
        }
    ],
    "portal_id": "2b047d7d-15a1-4d2f-8463-f89c2275bb73",
    "channel_name": "@PrawyTV",
    "provider": "claude",
    "insert_pinned_comment": False
}
result = process(task)

# 3. Zaplanowanie publikacji
schedule_res = schedule_short(
    short_id="<YT_SHORT_ID>",
    publish_at_utc="2026-09-15T07:00:00Z",
    title="Zoptymalizowany tytuł",
    description="Zoptymalizowany opis"
)
```

### Składnia CLI (Linia poleceń)

```powershell
# Diagnostyka i sprawdzenie tokenów
python agents/shorts-agent/worker.py --health

# Przetwarzanie z pliku JSON
python agents/shorts-agent/worker.py --task-file task.json

# Pobranie ostatniego stanu
python agents/shorts-agent/worker.py --status

# Zaplanowanie publikacji shorta
python agents/shorts-agent/scheduler.py --video-id <SHORT_ID> --publish-at "2026-09-15T07:00:00Z"

# Batch scheduling z pliku
python agents/shorts-agent/scheduler.py --batch-file schedule.json
```

---

## 3. Format wejścia i wyjścia

### Wejście: `process(task)`
```json
{
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
  "provider": "claude",
  "insert_pinned_comment": false
}
```

### Wyjście: `process(task)`
```json
{
  "status": "ok",
  "total": 1,
  "success": 1,
  "failed": 0,
  "results": [
    {
      "short_id": "slA15REfjpU",
      "source_youtube_id": "77ZwKDuOQ1M",
      "name": "Polska_konstytucja",
      "start_sec": 723.0,
      "end_sec": 773.5,
      "describe_status": "OK",
      "describe_result": {
        "optimized_title": "Konstytucja z 1997 roku jest pełna wad!",
        "description": "Dlaczego Polska potrzebuje reformy ustrojowej?",
        "hashtags": ["#Polska", "#Prawo", "#Konstytucja"],
        "pinned_comment": "Czy Twoim zdaniem obecna konstytucja wymaga zmian?"
      },
      "yt_update_status": "OK",
      "updated_title": "Konstytucja z 1997 roku jest pełna wad!",
      "error": null
    }
  ]
}
```

---

## 4. Konfiguracja i Zmienne Środowiskowe

| Zmienna | Domyślnie | Opis |
|---------|-----------|------|
| `VSE_URL` | `http://localhost:8085` | URL do VSE API |
| `VSE_API_HOST` | `localhost:8085` | Host VSE API |
| `SHORTS_PORTAL_ID` | `2b047d7d-15a1-4d2f-8463-f89c2275bb73` | Domyślny portal UUID (Prawy.pl) |
| `VSE_JWT` | *(auto)* | JWT do autoryzacji w VSE API |
| `YOUTUBE_OAUTH_TOKEN` | *(auto)* | Token OAuth2 do YouTube Data API |
| `SSH_HOST` | `ubuntu@147.224.162.100` | Host SSH serwera produkcyjnego |
| `SSH_KEY_PATH` | `~/.ssh/oracle-crimson.key` | Klucz SSH dla dostępu VPS |

---

## 5. Integracja z pipeline

```
Video źródłowe + punkty cięcia (task)
  ↓
Short Machine API (POST /v1/shorts/describe)
  ├── optimized_title (max 45 zn)
  ├── description (150-350 zn) + hashtags
  └── pinned_comment (pytanie polaryzujące)
  ↓
YouTube Data API v3 (videos.update)
  ├── snippet.title
  ├── snippet.description
  └── snippet.tags
  ↓
scheduler.py (videos.update snippet+status)
  ├── privacyStatus: 'private'
  └── publishAt: <ISO_TIMESTAMP_UTC>
```

---

## 6. Znane pułapki operacyjne

### P1 — Port wewnętrzny VSE to 8085 (nie 8000)
Wewnątrz sieci VPS i kontenerów port API VSE to zawsze 8085 (`http://localhost:8085`).

### P2 — Brak `#Shorts` w tytule i hashtagach
YouTube od 2024 roku automatycznie kwalifikuje wideo pionowe poniżej 60s jako Short. Umieszczanie `#Shorts` w tytule obniża CTR i marnuje cenne znaki na urządzeniach mobilnych.

### P3 — Zakaz linków URL w opisach Shortów
YouTube wyłączył klikalność linków w Shortach. Umieszczanie URL obniża zasięg organiczny algorytmu.

### P4 — Długość tytułu `optimized_title` max 45 znaków
Tytuły powyżej 45 znaków są obcinane wielokropkiem na ekranach smartfonów. Tytuł musi być „front-loaded”.

### P5 — `publishAt` wymaga bezwzględnie `privacyStatus: "private"`
YouTube Data API odrzuca zapytanie z błędem HTTP 400 jeśli `publishAt` jest wysyłane z innym statusem niż `private`.

### P6 — Tokeny OAuth do YouTube w bazie VSE
Endpoint `/v1/youtube/channels` zwraca jedynie metadane kanału, bez `access_token`. Prawdziwy token pobierany jest bezpośrednio z bazy przez `_build_credentials(ch).refresh()`.

### P7 — Provider LLM: `claude` (nie `gemini`)
Środowisko VPS posiada skonfigurowany klucz `ANTHROPIC_API_KEY`. Wybór `provider="gemini"` skutkuje błędem na serwerze.

### P8 — UUID portalu Prawy.pl
`portal_id` musi być pełnym ciągiem UUID (`2b047d7d-15a1-4d2f-8463-f89c2275bb73`), a nie stringiem `"prawy"`.

### P9 — Handle kanału: `@portalprawypl` (nie `@PrawyTV` ani `@naszkanal`)
VSE Short Machine i LLM mogą generować placeholder `@naszkanal`. Zawsze używać `DEFAULT_CHANNEL_NAME = "@portalprawypl"` w worker.py. Wynik z LLM należy weryfikować i czyścić przed wstrzyknięciem na YouTube.

### P10 — YouTube Data API Quota: 10 000 pkt/dzień, reset 09:00 CEST
`videos.list` = 1 pkt, `videos.update` = 50 pkt. Przy paczce 23 shortów = describe (23) + update (23×50) + scheduler (23 GET + 23 PUT) ≈ 2500 pkt. Limit wyczerpuje się przy dużych porcjach. Reset o 09:00 CEST (midnight Pacific). Monitorować zużycie. Skrypt `clean_descriptions.py` trzymać na końcu kolejki.

### P11 — OAuth re-autoryzacja przez VSE endpoint
Jeśli `invalid_grant: Token has been expired or revoked` — użyj endpointu VSE:
```bash
curl -H 'Authorization: Bearer <JWT>' http://localhost:8085/v1/youtube/oauth/login
# Zwraca authorization_url — otwórz w przeglądarce i zaloguj na prawypl5@gmail.com
```
CallbackURL: `https://vse.impresjapr.pl/v1/youtube/oauth/callback` — automatycznie zapisuje nowy refresh_token w bazie.

### P12 — AME Log jako źródło prawdy: filename → YouTube ID
Log Media Encoder: `C:\Users\tomas2\Documents\Adobe\Adobe Media Encoder\26.0\AMEEncodingLog.txt` (UTF-16LE)
Zawiera mapowanie: nazwa pliku shortsa → YouTube Video ID. Czytać przez PowerShell:
```powershell
Get-Content 'C:\Users\tomas2\Documents\Adobe\Adobe Media Encoder\26.0\AMEEncodingLog.txt' -Tail 300 -Encoding Unicode
```
Użytkownik sygnalizuje gotową paczkę komendą: "sprawdź logi media encoder".

---

## 7. Raport po zakończeniu

Po przetworzeniu paczki shortów, agent raportuje do Supervisora (`media-strateg`):

```markdown
[shorts-agent | DD.MM.YYYY HH:MM] STATUS

Liczba shortów: X przetworzonych / Y sukcesów / Z błędów
Przetworzone filmy:
  - <SHORT_ID_1> (<TYTUŁ>) — Describe: OK, YT: OK, Zaplanowano: <DATA>
  - <SHORT_ID_2> (<TYTUŁ>) — Describe: OK, YT: OK, Zaplanowano: <DATA>

Błędy i ostrzeżenia:
  - Brak / [opis błędu]
```

---

## 8. Architektura modułu

```python
# Lokalizacja: agents/shorts-agent/

agents/shorts-agent/
├── worker.py              # Główny silnik: describe + YT update
├── scheduler.py           # Planowanie: privacyStatus: private + publishAt
├── constitution.md        # Zasady operacyjne, standardy i znane pułapki
├── scripts/
│   └── clean_descriptions.py  # Czyszczenie @naszkanal → @portalprawypl w opisach YT
└── README.md              # Instrukcja obsługi
```

---

*Zaktualizowano: media-dev-42 | 15.09.2026 — P9-P12, handle @portalprawypl, AME log workflow, OAuth reauth*