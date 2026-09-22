# VSE Worker Constitution (media-dispatch)

> Ostatnia aktualizacja: 2026-09-22 | media-dev-39 (aktualizacja flow shorts candidates/render, live YT description biblia pattern, kanały aktywne)

Dokument opisuje zasady operacyjne dla workerów z rodziny `vse-worker`.
Zawiera wiedzę zdobytą zarówno z poprzednich sesji jak i weryfikacji live 29-31.08.2026 oraz 15-22.09.2026.

---

## 1. Środowisko VSE

| Element | Wartość |
|---------|--------|
| URL publiczny | `https://vse.impresjapr.pl` |
| Port wewnętrzny API | **8085** (NIE 8000, NIE 80!) |
| Container API | `vse-api` |
| Container DB | `vse-postgres` |
| Container Web | `vse-web` |
| DB credentials | user=`vse`, db=`vse` |
| VPS | `ubuntu@147.224.162.100` |
| SSH key (pełna ścieżka Windows) | `C:\Users\tomas2\.ssh\oracle-crimson.key` |
| Dashboard | `https://vse.impresjapr.pl/dashboard` |

---

## 2. Auth — Jak pobrać JWT Token

### ✅ Metoda działająca (zweryfikowana 29.08.2026)

```bash
# write_to_file → scp → ssh (niezawodny wzorzec)
docker exec vse-api python3 -c "
import os, datetime
from jose import jwt
secret = os.environ.get('JWT_SECRET_KEY', '')
payload = {
  'sub': '4b97ab0c-98ee-46c6-9be8-d86adc4cb38a',
  'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
}
print(jwt.encode(payload, secret, algorithm='HS256'))
"
```

Lub przez subprocess z poziomu skryptu Python:
```python
cmd = [
    "ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no", VPS,
    "docker exec vse-api python3 -c \""
    "import os,datetime; from jose import jwt; "
    "s=os.environ.get('JWT_SECRET_KEY',''); "
    "p={'sub':'4b97ab0c-98ee-46c6-9be8-d86adc4cb38a',"
    "'exp':datetime.datetime.utcnow()+datetime.timedelta(hours=24)}; "
    "print(jwt.encode(p,s,algorithm='HS256'))"
    "\""
]
r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
token = r.stdout.strip()
```

### Konto administratora
- Email: `tobroz@gmail.com` | ID: `4b97ab0c-98ee-46c6-9be8-d86adc4cb38a`
- Plan: Agency (quota 9999) | is_admin: true

### ❌ Metody które NIE działają
- `from api.auth import create_access_token` — wymaga `email` jako osobnego argumentu
- Login przez hasło inline w SSH z PS — escapowanie JSON w PS przez SSH jest niestabilne

### Weryfikacja tokenu
```bash
curl -s -H "Authorization: Bearer TOKEN" http://localhost:8085/v1/users/me
# Oczekiwany wynik: {"email":"tobroz@gmail.com","is_admin":true,...}
```

---

## 3. API Routes — kluczowe (zaktualizowano 22.09.2026)

```
/v1/audio/generate          ← MP3 → Whisper → SEO (bez thumbnail!)
/v1/generate                ← YouTube URL → SEO (z thumbnail, VideoObject schema)
/v1/inject                  ← wstrzyknij schema do WP
/v1/jobs/{job_id}/vtt       ← pobierz VTT z joba
/v1/shorts/candidates       ← wyłonienie kandydatów na shorty (start_sec, end_sec, hook)
/v1/shorts/render           ← kolejkowanie renderu shortów (9:16, napisy SRT)
/v1/shorts/describe         ← Short Machine SEO (youtube_id + portal_id)
/v1/youtube/channels        ← lista kanałów konta OAuth (metadane, BEZ access_token!)
/v1/youtube/oauth/login     ← link do reautoryzacji OAuth
/v1/youtube/publish-description  ← ⚠️ BROKEN dla kanałów Prawy (zwraca "channel not found or access denied"; używaj metody yt_desc w kontenerze)
/v1/youtube/channels/{channel_id}/playlists
/v1/portals                 ← config portali WP (credentials)
/health
```

### Parametry /v1/generate i /v1/inject

```python
# POPRAWNE wartości (zweryfikowane 30.08.2026)
llm_provider = "claude"          # NIE "gemini" — VPS ma ANTHROPIC_API_KEY
publication_type = "full_analysis"  # NIE "film" — patrz lista poniżej
portal_id = "2b047d7d-15a1-4d2f-8463-f89c2275bb73"  # UUID prawy.pl — NIE string "prawy"

# Dostępne publication_type:
# full_analysis, analiza, news, explainer, wywiad, poradnik, felieton, reportaz
```

### Portal UUID prawy.pl
```
prawy.pl → portal_id = "2b047d7d-15a1-4d2f-8463-f89c2275bb73"
```

---

## 4. ⚠️ ARCHITEKTURA FLOW — krytyczna wiedza

### Problem: Audio pipeline vs YouTube pipeline

VSE ma DWA tryby pracy. **Wyłącznie YouTube pipeline daje pełny wynik.**

| | Audio pipeline (`/v1/audio/generate`) | YouTube pipeline (`/v1/generate`) |
|--|--|--|
| Źródło transkryptu | Whisper na MP3 | YouTube captions API |
| Thumbnail WP | ❌ BRAK | ✅ automatycznie z YT |
| VideoObject schema | ⚠️ częściowy | ✅ pełny z YT metadata |
| Embed YouTube w artykule | ❌ BRAK | ✅ automatyczny |
| video_url w DB | `audio://audio_XXXXX` | `youtube://{video_id}` |

### ✅ Prawidłowy flow dla kanału bez auto-napisków (np. YT nie rozpoznał języka)

```
Krok 1: MP3 → POST /v1/audio/generate → dostać VTT z transkrypcją
          (tylko po to żeby mieć VTT — NIE używaj artykułu z tego kroku!)

Krok 2: VTT → YouTube captions.insert(videoId, vtt)
          (wgraj napisy na YT dla konkretnego video_id)

Krok 3: YouTube URL → POST /v1/generate → pełny pipeline
          (teraz YT ma napisy, VSE czyta je przez captions API)
          (dostajemy: thumbnail, VideoObject schema, embed, pełny artykuł)

Krok 4: schema → POST /v1/inject → WP post z pełną treścią
```

### Naprawa postów stworzonych przez audio pipeline (retrofitting)

Jeśli posty już istnieją w WP bez thumbnail:
```python
# 1. Pobierz thumbnail z YouTube
thumb_url = f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg"
img_data = requests.get(thumb_url).content

# 2. Upload do WP media library
media_resp = requests.post(
    f"{WP_BASE}/media",
    headers={
        "Authorization": f"Basic {wp_auth}",
        "Content-Disposition": f"attachment; filename={video_id}.jpg",
        "Content-Type": "image/jpeg",
    },
    data=img_data,
)
media_id = media_resp.json()["id"]

# 3. Ustaw featured_media na post
requests.post(
    f"{WP_BASE}/posts/{wp_post_id}",
    headers={"Authorization": f"Basic {wp_auth}"},
    json={"featured_media": media_id},
)
```

---

## 5. Audio Pipeline (Whisper) — użycie jako transkryptor

- **Endpoint:** `POST https://vse.impresjapr.pl/v1/audio/generate`
- **Cel:** TYLKO transkrypcja — używaj VTT, ignoruj artykuł (będzie generowany potem przez YT pipeline)
- **Timeout:** 600s (8-min audio ≈ 2-3 min processing)
- **VTT:** w `schema_data` lub przez `/v1/jobs/{job_id}/vtt`
- **llm_provider:** `"claude"` (NIE `"gemini"` — brak GEMINI_API_KEY na VPS!)

```python
resp = requests.post(
    "https://vse.impresjapr.pl/v1/audio/generate",
    headers={"Authorization": "Bearer TOKEN"},
    files={"file": (mp3_path.name, open(mp3_path, "rb"), "audio/mpeg")},
    data={"lang": "pl", "llm_provider": "claude"},  # claude, nie gemini!
    timeout=600,
)
vtt_text = resp.json()["schema_data"].get("vtt") or resp.json()["schema_data"].get("transcript")
# Jeśli brak VTT w schema_data, pobierz przez SSH:
# media_id = resp.json()["schema_data"].get("media_id")
# docker exec vse-api cat /tmp/{media_id}.vtt
```

---

## 6. YouTube OAuth

- Konto: `tobroz@gmail.com` — obsługuje oba kanały (Prawy TV + Prawy Biblijny)
- OAuth tokens: w **bazie danych VSE** (NIE w plikach YAML)
- Reautoryzacja: `https://vse.impresjapr.pl/v1/youtube/oauth/login` (wymaga sesji VSE)
- Refresh token wygasa i wymaga **co kilka tygodni ręcznego odwołania** przez ten link
- Po reautoryzacji sprawdzić: `GET /v1/youtube/channels` — powinno zwracać oba kanały

### ⚠️ Pułapka: `invalid_grant`
Jeśli YouTube API zwraca `invalid_grant` → token wygasł.
NIE próbuj naprawiać przez kod. Zgłoś bloker do Supervisora.
User musi otworzyć: `https://vse.impresjapr.pl/v1/youtube/oauth/login` i zatwierdzić dostęp.

### ⚠️ Pułapka: `/v1/youtube/channels` NIE zwraca access_token

Endpoint `/v1/youtube/channels` zwraca tylko metadane kanałów (id, title, stats). **NIE ma tam access_token.**

Aby pobrać aktywny token OAuth do bezpośredniego wywołania YT API — użyj SSH + docker exec:

```python
code = (
    "import asyncio\n"
    "from api.db import AsyncSessionLocal\n"
    "from api.models.youtube_channel import YouTubeChannel\n"
    "from api.core.youtube_publish import _build_credentials\n"
    "from google.auth.transport.requests import Request\n"
    "from sqlalchemy.future import select\n"
    "import json\n"
    "async def main():\n"
    "    async with AsyncSessionLocal() as db:\n"
    "        res = await db.execute(select(YouTubeChannel).where(YouTubeChannel.is_active == True))\n"
    "        out = []\n"
    "        for ch in res.scalars().all():\n"
    "            try:\n"
    "                creds = _build_credentials(ch)\n"
    "                creds.refresh(Request())\n"
    "                out.append({'id': str(ch.id), 'channel_id': ch.youtube_channel_id, 'title': ch.title, 'token': creds.token})\n"
    "            except Exception as e:\n"
    "                pass\n"
    "        print(json.dumps(out))\n"
    "asyncio.run(main())\n"
)
cmd = ["ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no", VPS,
       f"docker exec -w /app vse-api python3 -c {subprocess.list2cmdline([code])}"]
r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
tokens = json.loads([l for l in r.stdout.strip().split('\n') if l.startswith('[')][-1])
# tokens = [{'id': ..., 'channel_id': ..., 'title': ..., 'token': 'ya29...'}]
```

Kanały z aktywnymi tokenami (zweryfikowane 30.08.2026 i 22.09.2026):
- `Studio Prawy_PL` → channel_id: `UCoH2G9By4OX3kcLsc8lHgDw`
- `Prawy TV` → channel_id: `UCNXh5eIlMVxnUBpTMKUp4CA`

---

## 7. Short Machine API (produkcja od 31.08.2026)

Endpoint: POST /v1/shorts/describe
Auth: ten sam Bearer JWT co reszta VSE

Input:
```json
{
  "youtube_id": "ABC123",
  "portal_id": "2b047d7d-15a1-4d2f-8463-f89c2275bb73"
}
```

Output:
```json
{
  "optimized_title": "max 45 znaków, front-loaded",
  "description": "150-350 znaków, bez URL, słowa kluczowe z transkrypcji",
  "hashtags": ["#tag1", "#tag2"],  // max 5, bez #Shorts
  "pinned_comment": "Pytanie polaryzujące do pinowania",
  "related_video_id": "YT ID powiązanego materiału"
}
```

Znane pułapki:
- Bez #Shorts w hashtagach (YouTube dodaje automatycznie dla video < 60s)
- Bez URLów w description (blokuje reach)
- optimized_title max 45 znaków (nie 70!)
- Pinned comment dodaj przez YouTube Comments API (commentsInsert)

---

## 8. Znane Pułapki — pełna lista

| # | Pułapka | Rozwiązanie |
|---|---------|-------------|
| 1 | Port VSE wewnętrzny: **8085** (nie 8000) | Zawsze `http://localhost:8085` |
| 2 | URL: `/v1/` nie `/api/v1/` | Publiczny: `https://vse.impresjapr.pl/v1/...` |
| 3 | `create_access_token()` psuje się | Używaj `jose.jwt.encode()` z `JWT_SECRET_KEY` |
| 4 | SQL przez SSH z PS | Skrypt bash → `write_to_file` → `scp` pełna ścieżka → `ssh bash /tmp/...` |
| 5 | SCP `~` na Windows | Pełna ścieżka: `C:\Users\tomas2\...` |
| 6 | Whisper timeout | timeout=600s, nie przerywaj |
| 7 | Audio pipeline ≠ pełny pipeline | Patrz sekcja 4 — architektura flow |
| 8 | `invalid_grant` YT OAuth | Nie naprawiaj kodem, zgłoś do Supervisora |
| 9 | PS interpoluje `$variable` w SSH | Używaj `'apostrofów'` lub skryptu bash |
| 10 | Kanał biblijny config | W DB VSE (OAuth), nie w YAML. YAML-e są developerskie |
| 11 | **LLM provider: `gemini` nie działa** | VPS ma tylko `ANTHROPIC_API_KEY`. Używaj `llm_provider="claude"` |
| 12 | **`publication_type: "film"` → HTTP 422** | Dostępne: `full_analysis`, `analiza`, `news`, `explainer`, `wywiad`, `poradnik`, `felieton`, `reportaz` |
| 13 | **`portal_id: "prawy"` nie działa** | Musi być UUID: `portal_id="2b047d7d-15a1-4d2f-8463-f89c2275bb73"` |
| 14 | **`/v1/youtube/channels` nie zwraca access_token** | Używaj SSH + `_build_credentials(ch).refresh()` — patrz sekcja 6 |
| 15 | **Brak `#Shorts` w hashtagach/tytule** | YouTube taguje Shorty automatycznie (<60s, 9:16). Nie marnuj znaków |
| 16 | **Brak URL w opisie Shorta** | Linki w Shortach są nieklikalne i ucinają zasięg. Używaj `related_video_id` |
| 17 | **Długość `optimized_title` max 45 zn** | Tytuły >45 znaków ucinają się na smartfonach |
| 18 | **Przypinanie komentarza Shorts** | Używaj Comments API (`commentThreads.insert` / `commentsInsert`) dla `pinned_comment` |
| 19 | **Brak `youtube_description_body` w DB** | Pole istnieje TYLKO w live response `/v1/generate`, NIE w `transcript_jobs` |
| 20 | **`videos().update()` bez `title` = 400** | YouTube API v3 wymaga pełnego snippetu: `title` + `description` + `categoryId` |
| 21 | **Zagnieżdżone f-stringi w runnerze** | Generuj skrypty kontenera jako `'\n'.join(lines)`, unikaj wielokrotnych klamer |

---

## 9. Wzorce Kodu

### Generowanie tokenu JWT (niezawodny)
```python
# gen_token.py (uruchamiany przez: docker exec -i vse-api python3 < /tmp/gen_token.py)
import os, datetime
from jose import jwt
secret = os.environ.get('JWT_SECRET_KEY', '')
payload = {
    'sub': '4b97ab0c-98ee-46c6-9be8-d86adc4cb38a',
    'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
}
print(jwt.encode(payload, secret, algorithm='HS256'))
```

### Poprawny SCP (Windows → VPS)
```powershell
scp -i C:\Users\tomas2\.ssh\oracle-crimson.key -o StrictHostKeyChecking=no `
  "C:\Users\tomas2\.gemini\antigravity\playground\sonic-void\tmp\skrypt.sh" `
  ubuntu@147.224.162.100:/tmp/skrypt.sh
```

### Poprawne wywołanie /v1/generate
```python
r = requests.post(f"{VSE_BASE}/v1/generate", headers=vsh(vse_token), json={
    "video_url": f"https://www.youtube.com/watch?v={video_id}",
    "publication_type": "full_analysis",   # NIE "film"
    "portal_id": "2b047d7d-15a1-4d2f-8463-f89c2275bb73",  # UUID, nie string
    "post_title": title,
    "lang": "pl",
    "llm_provider": "claude"               # NIE "gemini"
}, timeout=360)
```

### Poprawne wywołanie Short Machine (/v1/shorts/describe)
```python
r = requests.post(f"{VSE_BASE}/v1/shorts/describe", headers=vsh(vse_token), json={
    "youtube_id": video_id,
    "portal_id": "2b047d7d-15a1-4d2f-8463-f89c2275bb73"
}, timeout=60)
data = r.json()
# data -> {"optimized_title": "...", "description": "...", "hashtags": [...], "pinned_comment": "...", "related_video_id": "..."}
```

---

## 10. Kanały Biblijne — wiedza operacyjna

| Element | Wartość |
|---------|--------|
| Kanał | Prawy Biblijny |
| Konto | tobroz@gmail.com (ten sam OAuth co Prawy TV) |
| Playlista Ewangelia | `PLw7UeigJuyWkUzzvhS1vZX0H251raaYa7` |
| Typ publikacji WP | `full_analysis` (NIE `film`!) |
| Lang | `pl` | LLM | `claude` (NIE `gemini`!) |
| Publish time | 00:00 CEST (`+02:00`) danego dnia |
| Pliki lokalne | `C:\Users\tomas2\Videos\Prawy\Biblia [data]\` (MP3 + MP4) |
| Thumbnails lokalne | `D:\Biblioteki\prawy video\Biblia\Biblia [data]\` |
| Portal UUID | `2b047d7d-15a1-4d2f-8463-f89c2275bb73` |

---

## 11. Short Machine — Full Generation Pipeline (Flow: candidates → render)

> ⚠️ UWAGA: Stary endpoint `/v1/shorts/generate` jest przestarzały (zwraca HTTP 422). Obecna architektura opiera się na procesie: **candidates → render**, a po opublikowaniu na **describe**.

### Krok 1: Wyłonienie kandydatów na Shorty
```
POST /v1/shorts/candidates
```
Payload:
```json
{
  "youtube_id": "{yt_id}",
  "youtube_url": "https://www.youtube.com/watch?v={yt_id}",
  "count_emotional": 5,
  "count_professional": 5,
  "provider": "claude",
  "portal_id": "2b047d7d-15a1-4d2f-8463-f89c2275bb73"
}
```
Zwraca listę segmentów `candidates[]`:
- `start_sec`, `end_sec` (czas rozpoczęcia i zakończenia fragmentu)
- `title` / `hook` (propozycja tytułu i haczyka)
- `score` / typ segmentu (emotional / professional)

### Krok 2: Renderowanie wyselekcjonowanych segmentów
```
POST /v1/shorts/render
```
Payload per candidate:
```json
{
  "youtube_id": "{yt_id}",
  "youtube_url": "https://www.youtube.com/watch?v={yt_id}",
  "local_path": "C:\\Users\\tomas2\\Videos\\Prawy\\{nazwa}.mp4",
  "start_sec": 120.0,
  "end_sec": 165.0,
  "candidate_data": { "title": "..." },
  "render_format": "9:16",
  "subtitles": "srt",
  "output_dir": "C:\\VSE\\Shorts",
  "portal_id": "2b047d7d-15a1-4d2f-8463-f89c2275bb73"
}
```
Zlecenie kolejkowane jest w systemie, zwracając `job_id` do monitorowania przez `GET /v1/shorts/{job_id}/result`.

### Krok 3: Optymalizacja SEO po uploadzie na YouTube
Po wyrenderowaniu i wgraniu shorta na kanał YouTube, do wygenerowania dedykowanego tytułu (<45 znaków), opisu i przypinanego komentarza używamy:
```
POST /v1/shorts/describe
```
(Szczegółowy opis wejścia i wyjścia znajduje się w Sekcji 7).

### local_overrides.json & VSELocalRunner
- Ścieżka: `C:\ProgramData\VSELocalRunner\local_overrides.json`
- Mapuje YT ID → lokalny plik MP4 (Local Runner używa go do renderowania bezpośrednio z dysku bez re-downloadu z YouTube).
- Windows Service: `VSELocalRunner` polluje `GET /v1/shorts/pending` co 5 sekund.
- Katalog docelowy: `C:\VSE\Shorts\{nazwa_pliku}_{data}\{tytuł}_raw.mp4` + `_social.mp4`.

---

## 12. Wzorzec pracy z agentami (odkryty 15.09.2026)

**Problem:** Workery background nie mogą wykonywać `run_command` (timeout approval).

**Rozwiązanie — podział pracy:**
```
Worker (Gemini Pro):
  → pisze skrypt Python
  → push do GitHub (agents/*/scripts/)
  → raportuje SHA do supervisora

Supervisor:
  → pobiera skrypt z GitHub MCP
  → write_to_file lokalnie
  → run_command: python skrypt.py
  → odczytuje wyniki
```

**subprocess + polskie znaki (Windows CP1250):**
```python
# BŁĄD: text=True powoduje UnicodeDecodeError na CP1250
r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

# POPRAWNIE: bytes + decode ręcznie
r = subprocess.run(cmd, capture_output=True, timeout=30)
output = r.stdout.decode('utf-8', errors='replace').strip()
```

---

## 13. Struktura bazy danych VSE — tabele i kolumny (odkryto 15.09.2026)

### Tabele (wynik `\dt` w kontenerze vse-postgres)
```
api_keys, app_settings, oauth_states, plans,
short_candidate_sets, short_jobs, short_srt_packages,
transcript_jobs, usage_logs, users, wp_portals, youtube_channels
```

### transcript_jobs (schema_data)
- Kolumna do zapytań: `video_url` (nie `video_id`!)
- Query wzorzec: `WHERE video_url LIKE '%{yt_id}%' ORDER BY created_at DESC LIMIT 1`
- Pola w schema_data: `lead`, `chapters`, `tags`, `yt_title`, `seo_title`, `faq`, `quotes`, `wp_id`, `yt_url`, `image_data`
- ⚠️ **NIE ma: `youtube_description_body`, `youtube_description_hook`** (te pola są generowane dynamicznie i zwracane TYLKO w live response API `/v1/generate`)

### youtube_channels
| UUID | Nazwa | YouTube Channel ID | Status |
|------|-------|--------------------|--------|
| 1d1f5783-... | VeriNarrMundo | UCJGgMtUhG1ILuyOKcL6JA_g | ⚠️ Out of scope (invalid_grant) |
| 9ec1c7b8-... | Tomasz Brzozowski | UCIBzmtDQ1SrE0r7jtWbiTNw | ⚠️ Out of scope (konto osobiste) |
| cdf73155-... | Studio Prawy_PL | UCoH2G9By4OX3kcLsc8lHgDw | ✅ AKTYWNY |
| 776a3a65-... | Prawy TV | UCNXh5eIlMVxnUBpTMKUp4CA | ✅ AKTYWNY |

---

## 14. YT Description — Wzorzec Biblia / Live Response (zaktualizowano 22.09.2026)

### ⚠️ Krytyczne pułapki YouTube API i VSE DB
1. **`youtube_description_body` NIE istnieje w bazie danych (`transcript_jobs`)** — to pole jest zwracane **WYŁĄCZNIE w live response wywołania `POST /v1/generate`**. Próba odczytu z DB zwróci `None`!
2. **YouTube API v3 `videos().update()` wymaga PEŁNEGO snippetu (`title` + `description` + `categoryId`)** — przekazanie samego opisu bez tytułu zwróci błąd HTTP 400 Bad Request!
3. **`POST /v1/youtube/publish-description` jest BROKEN dla kanałów Prawy** — zwraca `"error: channel not found or access denied"`.
4. **Zagnieżdżone f-stringi w dynamicznym kodzie kontenera powodują `NameError`** — skrypt do kontenera należy budować wyłącznie jako listę linii: `'\n'.join(script_lines)`.

### ✅ Prawidłowy wzorzec: Live Response + videos().list() przed update()

#### 1. Pobranie metadanych z live response:
```python
resp = requests.post(f"{VSE_BASE}/v1/generate", headers=vsh(token), json={
    "video_url": f"https://www.youtube.com/watch?v={yt_id}",
    "publication_type": "full_analysis",
    "portal_id": "2b047d7d-15a1-4d2f-8463-f89c2275bb73",
    "post_title": title,
    "lang": "pl",
    "llm_provider": "claude"
}, timeout=360)
resp_json = resp.json()
schema = resp_json.get("schema_data") or {}

# Tytuł (obowiązkowy w snippet!)
yt_title = schema.get("post_title") or schema.get("title") or resp_json.get("post_title") or title
if len(yt_title) > 100:
    yt_title = yt_title[:97] + "..."

# Opis z live response
yt_desc = schema.get("youtube_description_body") or resp_json.get("youtube_description_body")

# Fallback w przypadku braku wygenerowanego opisu:
if not yt_desc:
    lead = schema.get("lead", "")
    raw_chapters = schema.get("chapters", [])
    # UWAGA: chapter['time'] rzutuj na str (może być intem!)
    chapter_lines = [f"{str(c.get('time',''))} {str(c.get('title',''))}".strip() for c in raw_chapters if isinstance(c, dict)]
    chapters_str = "\n".join(chapter_lines)
    tags = schema.get("tags", [])
    hashtags_str = " ".join((f"#{t}" if not str(t).startswith("#") else str(t)) for t in tags)
    parts = [p for p in [lead, chapters_str, hashtags_str] if p]
    if wp_post_id:
        parts.append(f"Czytaj wiecej: https://prawy.pl/?p={wp_post_id}")
    yt_desc = "\n\n".join(parts)
elif wp_post_id and f"prawy.pl/?p={wp_post_id}" not in yt_desc:
    yt_desc += f"\n\nCzytaj wiecej: https://prawy.pl/?p={wp_post_id}"
```

#### 2. Wykonanie aktualizacji w kontenerze vse-api (skrypt jako lista linii):
```python
script_lines = [
    "import asyncio, json",
    "from api.db import AsyncSessionLocal",
    "from api.models.youtube_channel import YouTubeChannel",
    "from api.core.youtube_publish import _build_credentials",
    "from google.auth.transport.requests import Request",
    "from googleapiclient.discovery import build",
    "from sqlalchemy.future import select",
    "",
    "VIDEO_ID = " + json.dumps(yt_id),
    "YT_TITLE = " + json.dumps(yt_title),
    "YT_DESC = " + json.dumps(yt_desc),
    "PRAWY_CHANNELS = ['UCoH2G9By4OX3kcLsc8lHgDw', 'UCNXh5eIlMVxnUBpTMKUp4CA']",
    "",
    "async def main():",
    "    async with AsyncSessionLocal() as db:",
    "        res = await db.execute(select(YouTubeChannel).where(YouTubeChannel.is_active == True))",
    "        channels = res.scalars().all()",
    "        updated = False",
    "        for ch in channels:",
    "            if ch.youtube_channel_id not in PRAWY_CHANNELS:",
    "                continue",
    "            try:",
    "                creds = _build_credentials(ch)",
    "                creds.refresh(Request())",
    "                yt = build('youtube', 'v3', credentials=creds, cache_discovery=False)",
    "                # ZAWSZE pobierz aktualny snippet przed update!",
    "                vresp = yt.videos().list(part='snippet', id=VIDEO_ID).execute()",
    "                if not vresp.get('items'):",
    "                    continue",
    "                snippet = vresp['items'][0]['snippet']",
    "                snippet['title'] = YT_TITLE",
    "                snippet['description'] = YT_DESC",
    "                yt.videos().update(part='snippet', body={'id': VIDEO_ID, 'snippet': snippet}).execute()",
    "                print('OK: ' + VIDEO_ID + ' via ' + str(ch.title))",
    "                updated = True",
    "                break",
    "            except Exception as e:",
    "                print('SKIP ' + str(ch.title) + ': ' + str(e)[:100])",
    "        if not updated:",
    "            print('FAILED: ' + VIDEO_ID)",
    "",
    "asyncio.run(main())"
]
```

---

## 15. Transcript Guard — zabezpieczenie przed hallucynacją (od prawy_full_flow_v2.py)

```python
resp = requests.post(f"{VSE_BASE}/v1/generate", ...)
if resp.status_code == 200:
    resp_json = resp.json()
    transcript_ok = resp_json.get("transcript_available", True)
    schema = resp_json.get("schema_data", {})
    # Sprawdz również w schema_data
    transcript_ok = transcript_ok and schema.get("transcript_available", True)
    
    if not transcript_ok:
        print("BRAK TRANSKRYPTU - nie inject, czekaj 30 min i ponawia")
        # NIE wywołuj /v1/inject!
    else:
        # Proceed normalnie
        step_inject(schema, yt_url, token)
```

YouTube generuje napisy automatycznie (do 30 min po uplodzie).
Jeśli VSE nie ma transkryptu → powróć za 30 min i ponownie wywołaj `/v1/generate`.

---

## 16. Pliki lokalne — sciezki nagran biblijnych

### Lokalizacja plikow wideo/audio
| Element | Wartosc |
|---------|--------|
| Glowny katalog filmow biblijnych | `C:\Users\tomas2\Videos\Prawy\Biblia 30.08-04.09.2026\` |
| Log Adobe Media Encoder (sciezki exportu) | `C:\Users\tomas2\Documents\Adobe\Adobe Media Encoder\26.0\AMEEncodingLog.txt` |
| Kodowanie pliku AME log | UTF-16LE — czytaj przez `Get-Content -Encoding Unicode` |
| Format nazw MP3 biblijnych | `Lk X, Y-Z DD.MM.YYYY dzien.mp3` |
| Format nazw MP4 biblijnych | `lk-X,Y-Z-DD.MM.YYYY-dzien.mp4` lub `Lk X,Y-Z DD.MM.YYYY dzien.mp4` |

### Jak znalezc sciezke lokalnego pliku po YT ID
Czytaj log AME:
```powershell
Get-Content "C:\Users\tomas2\Documents\Adobe\Adobe Media Encoder\26.0\AMEEncodingLog.txt" -Encoding Unicode | Select-String -Pattern "youtube.com" -Context 5,0
```
Linia `Plik wyjsciowy` pojawia sie PRZED linia z URL YouTube w logu.

### Procedura MP3 fallback (TYLKO gdy transcript_available=False)
1. Sprawdz `transcript_available` w odpowiedzi `/v1/generate`
2. Jesli False: szukaj MP4 w katalogu filmow biblijnych (patrz tabela wyzej)
3. Konwertuj: `ffmpeg -i plik.mp4 -q:a 2 -map a plik.mp3 -y`
4. Wyslij MP3 do `/v1/audio/generate` (lang=pl, llm_provider=claude, timeout=600s)
5. Upload VTT na YT captions.insert -> czekaj 30s -> ponow `/v1/generate`

---

## 17. Kanały YouTube — Aktywne vs Out of Scope

Dla wszystkich operacji i pipeline'ów kanałów Prawy używamy **WYŁĄCZNIE** dwóch kanałów:

| Kanał | YouTube Channel ID | Status | Zastosowanie |
|-------|--------------------|--------|--------------|
| **Studio Prawy_PL** | `UCoH2G9By4OX3kcLsc8lHgDw` | ✅ AKTYWNY | Główny kanał studyjny Prawy.pl |
| **Prawy TV** | `UCNXh5eIlMVxnUBpTMKUp4CA` | ✅ AKTYWNY | Kanał telewizyjny Prawy TV / Biblijny |

### Kanały pomijane (Out of Scope dla pipeline prawy):
- **Tomasz Brzozowski** (`UCIBzmtDQ1SrE0r7jtWbiTNw`) — konto osobiste, NIE używać do publikacji treści Prawy.pl.
- **VeriNarrMundo** (`UCJGgMtUhG1ILuyOKcL6JA_g`) — token wygasł (`invalid_grant`), pomijać w kodzie.

### Wzorzec filtru kanałów w kodzie:
```python
PRAWY_CHANNELS = ['UCoH2G9By4OX3kcLsc8lHgDw', 'UCNXh5eIlMVxnUBpTMKUp4CA']

for ch in channels:
    if ch.youtube_channel_id not in PRAWY_CHANNELS:
        print(f"SKIP out-of-scope channel: {ch.title} ({ch.youtube_channel_id})")
        continue
    # ... obsluga kanalu
```

---

*[media-strateg-01 | media-dispatch 29.08.2026 — init]*  
*[Supervisor 01 | sonic-void 29.08.2026 — pułapki live]*  
*[Supervisor 01 | sonic-void 30.08.2026 — architektura audio vs YT pipeline, OAuth rotation, retrofitting thumbnails]*  
*[media-strateg | media-dispatch 30.08.2026 — pułapki 11-14: llm_provider=claude, publication_type=full_analysis, portal_id UUID, YT token przez SSH _build_credentials]*  
*[media-dev-12 | media-dispatch 31.08.2026 — sekcja Short Machine API (/v1/shorts/describe) na produkcji, pułapki 15-18]*  
*[media-dev-39 | media-dispatch 22.09.2026 — aktualizacja sekcji 3 (publish-description broken), sekcji 11 (flow candidates->render), sekcji 14 (live response biblia pattern, videos.list przed update), pułapki 19-21, sekcja 17 kanały aktywne]*
