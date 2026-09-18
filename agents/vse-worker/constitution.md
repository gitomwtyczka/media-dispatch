# vse-worker — Konstytucja

> Plik operacyjny dla agentów AI wywołujących i rozwijających `vse-worker`.  
> Ostatnia aktualizacja: 12.09.2026 | media-dev-C

---

## 1. Tożsamość

| Pole | Wartość |
|------|--------|
| **Callsign** | `vse-worker` |
| **Warstwa** | Production (Warstwa 3) |
| **Stack** | Python 3.12+ · requests · googleapiclient · docker exec · PostgreSQL / FastAPI |
| **Środowisko** | VPS (`ubuntu@147.224.162.100`) lub lokalny PC przez SSH |
| **Główne moduły** | `agents/vse-worker/pipeline.py` · `agents/vse-worker/worker.py` |
| **VSE Port wewnętrzny** | **8085** (NIE 8000, NIE 80!) |
| **VSE URL publiczny** | `https://vse.impresjapr.pl` |

---

## 2. Architektura 4-stopniowego Pipeline'u

```
Wejście: video_url / video_id
   │
   ├─► KROK 1: Generowanie SEO & Artykułu (POST /v1/generate)
   │   • LLM provider: claude (VPS posiada ANTHROPIC_API_KEY)
   │   • Typ publikacji: full_analysis
   │   • Generuje: yt_title, seo_title, post_title, chapters, tags, wp_content
   │
   ├─► KROK 2: Wstrzyknięcie do WordPress (POST /v1/inject)
   │   • Cel: portal UUID (np. prawy.pl = 2b047d7d-15a1-4d2f-8463-f89c2275bb73)
   │   • ⛔ post_status: ZAWSZE 'draft' (nigdy 'publish' bez zgody)
   │   • Zwraca: wp_post_id oraz post_url
   │
   ├─► KROK 3: Aktualizacja metadanych YouTube (docker exec w vse-api)
   │   • Pobranie poświadczeń OAuth z bazy VSE (tabela YouTubeChannel)
   │   • Złożenie opisu: hook + body + link do artykułu WP + mid CTA + rozdziały + credits + hashtagi
   │   • ⛔ privacyStatus: ZAWSZE 'unlisted' (nigdy 'public')
   │   • Długość tytułu: obcinana bezpiecznie do max 100 znaków
   │
   └─► KROK 4: Shorts Machine (Kandydaci & Render)
       • POST /v1/shorts/candidates: wyłonienie propozycji (emocjonalne i eksperckie)
       • POST /v1/shorts/render: jeśli podano local_path, zlecenie renderu pionowego 9:16 z napisami SRT
```

---

## 3. Specyfikacja Wejścia i Wyjścia

### Wejście: `task` dictionary

```python
task = {
    "video_url": "https://www.youtube.com/watch?v=EnclbKLEDAA",
    "video_id": "EnclbKLEDAA",                                   # opcjonalne jeśli podano URL
    "local_path": "/home/ubuntu/video-seo-engine/batch/input.mp4", # opcjonalne (dla renderu)
    "portal_id": "2b047d7d-15a1-4d2f-8463-f89c2275bb73",         # opcjonalne, default z env
    "channel_id": "UCoH2G9By4OX3kcLsc8lHgDw",                     # opcjonalne
    "provider": "claude",                                         # opcjonalne (default: claude)
    "steps": [1, 2, 3, 4],                                        # opcjonalne (selekcja kroków)
    "output_dir": "/home/ubuntu/VSE/Shorts"                       # opcjonalne
}
```

### Wyjście: format odpowiedzi

```json
{
  "status": "ok",
  "step1_generate": {
    "status": "ok",
    "status_code": 200,
    "schema_data": { ... }
  },
  "step2_inject": {
    "status": "ok",
    "status_code": 200,
    "wp_post_id": 12345,
    "post_url": "https://prawy.pl/?p=12345"
  },
  "step3_yt_update": {
    "status": "ok",
    "title": "Tytuł filmu",
    "privacyStatus": "unlisted"
  },
  "step4_shorts": {
    "status": "ok",
    "candidates": [ ... ],
    "render_jobs": [
      {
        "job_id": "job_987",
        "title": "Fragment...",
        "start_sec": 15.0,
        "end_sec": 50.0,
        "status": "submitted"
      }
    ]
  }
}
```

---

## 4. Konfiguracja Środowiska i Autoryzacja

### Zmienne środowiskowe

- `VSE_URL`: `http://localhost:8085` (wewnątrz VPS) lub `https://vse.impresjapr.pl`
- `VSE_JWT_TOKEN`: opcjonalny pre-generowany token
- `VSE_PORTAL_ID`: default `2b047d7d-15a1-4d2f-8463-f89c2275bb73`
- `VSE_CHANNEL_ID`: default `UCoH2G9By4OX3kcLsc8lHgDw`
- `VSE_OUTPUT_DIR`: default `/home/ubuntu/VSE/Shorts`
- `VSE_SSH_KEY`: default `C:\Users\tomas2\.ssh\oracle-crimson.key`
- `VSE_VPS_HOST`: default `ubuntu@147.224.162.100`

### Dynamiczne generowanie JWT

Gdy `VSE_JWT_TOKEN` nie jest zdefiniowany, worker automatycznie pozyskuje token poprzez wykonanie kodu w kontenerze `vse-api`:
```python
import os, datetime
from jose import jwt
secret = os.environ.get('JWT_SECRET_KEY', '')
payload = {
    'sub': '4b97ab0c-98ee-46c6-9be8-d86adc4cb38a',
    'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
}
token = jwt.encode(payload, secret, algorithm='HS256')
```

---

## 5. ⛔ Bezwzględne Zasady Operacyjne

1. **WordPress status:** ZAWSZE `post_status='draft'`. Publikacja (`publish`, `future`) wymaga wyraźnej decyzji użytkownika lub akceptacji w arkuszu.
2. **YouTube status:** ZAWSZE `privacyStatus='unlisted'`. Zakaz samowolnego ustawiania na `public`.
3. **Zakaz hardcodowania sekretów:** Tokeny JWT, poświadczenia OAuth, hasła bazodanowe nie mogą znajdować się w kodzie repozytorium.
4. **Bezpieczny transport do kontenera:** Cały kod lub payload przesyłany do `docker exec` / SSH jest enkodowany w base64, co zapobiega psuciu znaków przez powłoki (PowerShell / Bash).
5. **Konto VSE:** ZAWSZE `tobroz@gmail.com` (USER_ID: `4b97ab0c-98ee-46c6-9be8-d86adc4cb38a`). To konto ma OAuth dla wszystkich kanałów YT. Nie używać innych kont.

---

## 6. Znane Pułapki Operacyjne

| # | Pułapka | Objaw | Rozwiązanie |
|---|---------|-------|-------------|
| **P1** | Zły port VSE | Connection Refused na porcie 8000 | Port wewnętrzny to **8085** (`http://localhost:8085`) |
| **P2** | Zła ścieżka API | 404 Not Found przy `/api/v1/...` | W VSE prefiks to `/v1/...` |
| **P3** | Provider `gemini` | Błąd 500 / brak klucza | VPS posiada tylko `ANTHROPIC_API_KEY`. Zawsze stosuj `provider="claude"` |
| **P4** | `publication_type: "film"` | Błąd HTTP 422 Unprocessable Entity | Prawidłowa wartość to `publication_type="full_analysis"` |
| **P5** | Portal ID jako string alias | Błąd w bazie portali | Wymagany pełny UUID: `2b047d7d-15a1-4d2f-8463-f89c2275bb73` |
| **P6** | `invalid_grant` YouTube OAuth | Błąd odświeżania tokenu Google | Token wygasł — nie naprawiać kodem, zgłosić do Supervisora (reautoryzacja pod adresem `/v1/youtube/oauth/login`) |
| **P7** | Przekroczenie limitu znaków tytułu YT | Błąd API YouTube | Tytuł YT ma twardy limit 100 znaków — skrypt tnie go do 97 + `...` |
| **P8** | Escapowanie w PowerShell / SSH | Składniowe błędy parsowania | Wszelkie skrypty i JSONy do `docker exec` przesyłać jako ciągi base64 |
| **P9** | Brak pliku `local_path` | Błąd renderowania shorta | Gdy brak pliku lokalnego, Krok 4 generuje kandydatów i raportuje rendering jako `skipped` |

---

## 7. Raportowanie po Zakończeniu

Każde wykonanie workera kończy się ustrukturyzowanym raportem w formacie:

```
[vse-worker | DD.MM.YYYY HH:MM] STATUS

Video: <video_url> (<video_id>)
Kroki: <wykonane kroki>

Wyniki:
  - Krok 1 (Generate): OK / ERROR
  - Krok 2 (Inject WP): OK (post_id: #..., url: ...) / ERROR
  - Krok 3 (YouTube Metadata): OK (status: unlisted) / ERROR
  - Krok 4 (Shorts): OK (X kandydatów, Y render jobs) / ERROR

Błędy / Uwagi: <szczegóły jeśli wystąpiły>
```

---

## 8. Handoff do emisja-worker — architektura

> Zasada: vse-worker produkuje. emisja-worker wprowadza do redakcji.

### Punkt handoffu

Po zakończeniu Kroku 2 (`/v1/inject`) vse-worker posiada:
- `wp_post_id` — ID wpisu WordPress
- `wp_edit_url` — URL edycji draftu w WP Admin

Te dane są **wejściem do emisja-worker**.

### Flow

```
vse-worker
  Krok 1: /v1/generate → SEO + artykuł
  Krok 2: /v1/inject   → WP draft (zwraca wp_post_id + wp_edit_url)
  Krok 3: YT metadata update
  Krok 4: Short Machine
       │
       ▼ HANDOFF (przekazuje wp_post_id)
  emisja-worker
    → draft-collab link (wtyczka WP)
    → zapis do Sheets zakładka "Emisja"
    → redaktor/korektor dostaje link bez konta WP
```

### Trigger emisja-worker

emisja-worker jest wywoływany:
- **Automatycznie** — gdy vse-worker zakończy pipeline z sukcesem (przyszła integracja)
- **Manualnie** — Supervisor dispatchuje emisja-worker podając `wp_post_id` z raportu vse-worker

### Dane przekazywane

```python
# Wyjście vse-worker (wejście emisja-worker)
handoff = {
    "wp_post_id": 12345,
    "wp_edit_url": "https://prawy.pl/wp-admin/post.php?post=12345&action=edit",
    "portal_id": "2b047d7d-15a1-4d2f-8463-f89c2275bb73",
    "video_id": "z2ZlzcNsNwQ",
    "title": "Tytuł materiału"
}
```

### Status (12.09.2026)

- ✅ Architektura zdefiniowana i przetestowana
- ✅ Oba workery zbudowane i w repo
- 🔵 Automatyczny trigger (vse → emisja bez Supervisora) — Faza 2 integracji

---

## 9. Kanoniczne wywołanie — bez ad-hoc skryptów

> Zasada: NIE tworzyć jednorazowych skryptów (halwa_pipeline.py, full_flow_vX.py itp.).
> Zawsze używać `agents/vse-worker/worker.py` jako jedynego punktu wejścia.

### Wywołanie na VPS

```bash
# Jeden film
ssh -i C:\Users\tomas2\.ssh\oracle-crimson.key -o StrictHostKeyChecking=no ubuntu@147.224.162.100 \\
  "cd /home/ubuntu/media-dispatch && python3 agents/vse-worker/worker.py --video-id z2ZlzcNsNwQ"

# Diagnostyka
python3 agents/vse-worker/worker.py --health
python3 agents/vse-worker/worker.py --status

# Selektywne kroki (np. tylko Short Machine)
python3 agents/vse-worker/worker.py --video-id z2ZlzcNsNwQ --steps 4

# Pełny pipeline z local_path (render shortów)
python3 agents/vse-worker/worker.py --video-id z2ZlzcNsNwQ --local-path /home/ubuntu/VSE/input/film.mp4
```

### Parametry CLI

| Parametr | Opis |
|----------|------|
| `--video-id` | YouTube ID (11 znaków) |
| `--video-url` | Pełny URL YouTube |
| `--steps` | Np. `1,2,3,4` (domyślnie wszystkie) |
| `--local-path` | Lokalna ścieżka MP4 (dla render shortów) |
| `--portal-id` | Override portal UUID |
| `--channel-id` | Override channel ID |
| `--health` | Sprawdź połączenie VSE + JWT |
| `--status` | Stan ostatniego zadania |

---

## 10. Short Machine — Faza 2 (po uploadzie shortów)

### Kontekst

Krok 4 pipeline'u (`/v1/shorts/candidates`) generuje kandydatów w VSE dashboard.
Użytkownik obrabia kandydatów w Premiere i uploaduje na YouTube ręcznie.
Po uploadzie — agent czyta logi Adobe Media Encoder i wywołuje `shorts/describe`.

### Trigger Fazy 2

Użytkownik mówi: „uploadołem shorty, YT IDs: [lista]”

### Flow Fazy 2

```
User: "uploadowane shorty, YT IDs: [ABC123, DEF456]"
  │
  ├─► Parsuj logi AME: C:\Users\tomas2\Documents\Adobe\Adobe Media Encoder\26.0\AMEEncodingLog.txt
  │   (encoding: UTF-16LE, skrypt: parse_ame_log.py)
  │   → mapuje pliki exportów → ścieżki w C:\VSE\Shorts\\
  │
  └─► POST /v1/shorts/describe dla każdego shorta:
      payload: {"youtube_id": "[YT ID shorta]", "portal_id": "2b047d7d-15a1-4d2f-8463-f89c2275bb73"}
      → aktualizuje tytuł, opis, tagi, pinned comment na YT
```

### Zasady Fazy 2

- Zachowaj `privacy` i `publishAt` — nie nadpisuj zaplanowanej emisji
- Tagi format: `#tag` (z hashtagiem)
- Pinned comment: opcjonalnie przez `commentThreads().insert`
- Skrypt referencyjny: `agents/shorts-agent/worker.py` (process_shorts_describe)

### Parametry

- AME log: `C:\Users\tomas2\Documents\Adobe\Adobe Media Encoder\26.0\AMEEncodingLog.txt` (UTF-16LE)
- Shorty eksport: `C:\VSE\Shorts\<Nazwa projektu>_YouTube_<Data>\`
- Endpoint: `POST http://localhost:8085/v1/shorts/describe`
- PORTAL_ID: `2b047d7d-15a1-4d2f-8463-f89c2275bb73`

---

## 11. Architektura dwóch workerów — pełny end-to-end flow

```
Użytkownik: "nowe wideo: [YouTube ID]"
       │
       ▼
vse-worker
  ├─ Krok 1: /v1/generate (SEO, artykuł, rozdziały)
  ├─ Krok 2: /v1/inject → WP draft [wp_post_id]
  ├─ Krok 3: YT metadata update (tytuł + opis + link WP)
  └─ Krok 4: /v1/shorts/candidates → VSE Short Machine dashboard
       │
       ▼ [wp_post_id]
emisja-worker
  ├─ draft-collab link → link do podglądu bez konta WP
  └─ zapis do Google Sheets (zakładka "Emisja") → redaktor
       │
       ▼ [user obrabia shorty w Premiere, uploaduje na YT]
vse-worker (Faza 2 — shorts/describe)
  └─ logi AME → POST /v1/shorts/describe → opisy na YT shorts
       │
       ▼
Publikacja (ręcznie lub scheduler)
```

### Trigger-chain

| Etap | Trigger | Worker |
|------|---------|--------|
| Nowe wideo na YT | User mówi YT ID | vse-worker |
| WP draft gotowy | Automatyczny po Kroku 2 | emisja-worker |
| Shorty uploadowane | User mówi YT IDs shortów | vse-worker Faza 2 |
| Publikacja | Akceptacja w Sheets | scheduler |
