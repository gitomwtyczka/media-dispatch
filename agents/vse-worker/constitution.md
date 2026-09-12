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
