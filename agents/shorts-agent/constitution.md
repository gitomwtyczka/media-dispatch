# shorts-agent — Konstytucja

> Plik dla agentów AI które wywołują shorts-agent.  
> Ostatnia aktualizacja: 15.09.2026 | media-strateg

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

### P13 — Hook text na thumbnail: max 4 SENSOWNE słowa
Hook z VSE (candidate_data.hook_text) to pełne zdanie — za długie na thumbnail.
Zasada: wybierz max 4 słowa które razem mają sens. NIE ucinaj mechanicznie pierwszych 4.

Przykłady:
- "Pakt Ribbentrop-Mołotow nie dotyczył tylko Polski" → `PAKT RIBBENTROP-MOŁOTOW`
- "Komisja reprywatyzacyjna - PiS vs PO" → `KOMISJA REPRYWATYZACYJNA`
- "Bruksela dyktuje diety jak ZSRR 50 lat temu" → `BRUKSELA DYKTUJE DIETY`

Algorytm: preferuj optimized_title (krótszy). Jeśli za długi — weź kluczowe 4 słowa z hook_text.

### P14 — Apla dynamiczna: rośnie w dół z tekstem
APLA (ciemny panel) NIE ma stałego dolnego marginesu — rozszerza się z tytułem.
Brak limitu wierszy — tytuł może mieć 5+ słów, apla podąża za nim.

```python
apla_bottom = max(1759, title_bottom + 60)
redbar_bottom = apla_bottom
guest_top = title_bottom + 20
guest_bottom = title_bottom + 90
```

### P15 — VSE DB + AME log = dwuetapowy flow shortów

**Etap 1 — VSE Short Machine renderuje short:**
- Wynik zapisywany w `short_jobs`: `result_paths->>'raw'` = lokalna ścieżka MP4
- Na tym etapie **NIE MA jeszcze** `yt_short_video_id` (nie było uploadu)

**Etap 2 — User uploaduje z Premiere Pro na YouTube:**
- YouTube przypisuje `video_id`
- User informuje agenta: `"sprawdź logi media encoder"` = sygnał startu
- **AME log** (`AMEEncodingLog.txt`, UTF-16LE) = oficjalny most między etapem 2 a systemem
- Zawiera pary: `raw_mp4_filename → youtube_video_id` po uploadzie z Premiere

**Fix architektoniczny po wykryciu sygnału "sprawdź logi ME":**
1. Czytaj AME log (UTF-16LE) → wyciągnij pary: `raw_mp4_filename → yt_video_id`
2. Matchuj z `short_jobs WHERE result_paths->>'raw' LIKE '%nazwa_pliku%'`
3. Zapisz: `UPDATE short_jobs SET yt_short_video_id = yt_video_id WHERE id = matched_id`
4. Dopiero potem: inject metadata na YouTube

**Schema VSE DB (tabela short_jobs):**
- `result_paths->>'raw'` = pełna ścieżka lokalna MP4 ✅
- `candidate_data->>'hook_text'` = hook (pełne zdanie) ✅
- `candidate_data->>'optimized_title'` = tytuł YT ✅
- `youtube_id` = source video ID (NIE ID shorta!)
- `yt_short_video_id` = ❌ GAP — brakuje! Do dodania:

```sql
ALTER TABLE short_jobs ADD COLUMN yt_short_video_id varchar(20);
```

**Query dla workera thumbnail:**
```sql
SELECT result_paths->>'raw' as mp4_path,
       candidate_data->>'hook_text' as hook,
       candidate_data->>'optimized_title' as title,
       created_at
FROM short_jobs
WHERE status = 'done'
  AND result_paths->>'raw' IS NOT NULL
  AND created_at >= '2026-09-09'
ORDER BY created_at;
```

**Flow docelowy:**
```
AME log → yt_video_id → match short_jobs → result_paths->>'raw' → ffmpeg t=5s → thumbnail
```

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


## Thumbnail Pipeline (v9, finalny)

### Stack
- Pillow (lokalnie)
- Font: NimbusSansNarrow-Bold.otf z branding kitu
- Branding kit: `D:\Biblioteki\prawy video\!_shortsy identyfikacja 9x16\prawy-shorts-kit\`

### Współrzędne (z PSD wzorcowego 1080x1920)
| Element | left | top | right | bottom |
|---|---|---|---|---|
| Badge (01-overlay-staly) | 92 | 76 | 498 | 288 |
| CTA (02-05 rotacyjnie) | 131 | 211 | 913 | 394 |
| Apla (ciemny panel) | 0 | 664 | 1080 | 1759 |
| Czerwona kreska | 105 | 664 | 116 | 1759 |
| Strefa tytułu | 151 | 739 | 1017 | 1508 |
| Strefa gości | 151 | 1629 | 942 | 1699 |

### Tytuł — auto-fit
Każde słowo hook_text osobna linia, auto-fit do max szerokości 866px.
Font: bialy, stroke czarny 5px.

### Goście — auto-fit
Jedna linia, auto-fit do 791x70px. Kolor: #E31335.

### Tło — priorytet URL
1. `oar2.jpg` (pionowe YT thumb)
2. `oardefault.jpg`
3. `maxresdefault.jpg`
4. Fallback: NAVY #07152B

### Wywołanie
```python
from agents.shorts_agent.thumbnail_generator import generate_thumbnail
path = generate_thumbnail('Ud39NRwg6bc', 'BRUKSELA DYKTUJE DIETY', 'PŁUŻAŃSKI — OSOWSKI', cta_idx=2)
```

### Output
`C:\VSE\Shorts\thumbnails\{video_id}_thumbnail.jpg`