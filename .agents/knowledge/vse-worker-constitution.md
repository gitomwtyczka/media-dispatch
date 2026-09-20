# VSE Worker Constitution (media-dispatch)

> Ostatnia aktualizacja: 2026-08-31 | media-dev-12 (wdrożenie Short Machine API /v1/shorts/describe)

Dokument opisuje zasady operacyjne dla workerów z rodziny `vse-worker`.
Zawiera wiedzę zdobytą zarówno z poprzednich sesji jak i weryfikacji live 29-31.08.2026.

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

## 3. API Routes — kluczowe (31.08.2026)

```
/v1/audio/generate          ← MP3 → Whisper → SEO (bez thumbnail!)
/v1/generate                ← YouTube URL → SEO (z thumbnail, VideoObject schema)
/v1/inject                  ← wstrzyknij schema do WP
/v1/jobs/{job_id}/vtt       ← pobierz VTT z joba
/v1/shorts/describe         ← Short Machine SEO (youtube_id + portal_id)
/v1/youtube/channels        ← lista kanałów konta OAuth (metadane, BEZ access_token!)
/v1/youtube/oauth/login     ← link do reautoryzacji OAuth
/v1/youtube/publish-description  ← update opisu na YT
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

Kanały z aktywnymi tokenami (zweryfikowane 30.08.2026):
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
}, timeout=300)
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

## 11. Short Machine — Full Generation Pipeline

### Endpoint generowania shortów
```
POST /v1/shorts/generate
```

Payload:
```json
{
  "youtube_url": "https://www.youtube.com/watch?v={yt_id}",
  "youtube_id": "{yt_id}",
  "portal_id": "2b047d7d-15a1-4d2f-8463-f89c2275bb73",
  "count_emotional": 5,
  "count_professional": 5,
  "local_path": "C:\\Users\\tomas2\\Videos\\Prawy\\{nazwa}.mp4",
  "render_config": {"format": "9:16", "output_dir": "C:\\VSE\\Shorts"}
}
```

### local_overrides.json
- Ścieżka: `C:\ProgramData\VSELocalRunner\local_overrides.json`
- Mapuje YT ID → lokalny plik MP4
- Local Runner używa go do cięcia bez pobierania z YT

### VSELocalRunner
- Windows Service: `VSELocalRunner`
- Polluje `GET /v1/shorts/pending` co 5 sekund
- Output: `C:\VSE\Shorts\{nazwa_pliku}_{data}\{tytuł}_raw.mp4` + `_social.mp4`

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
- NIE ma: `youtube_description_body`, `youtube_description_hook` (te pola są tylko w API response)

### youtube_channels
| UUID | Nazwa | YouTube Channel ID |
|------|-------|------------------|
| 1d1f5783-... | VeriNarrMundo | UCJGgMtUhG1ILuyOKcL6JA_g |
| 9ec1c7b8-... | Tomasz Brzozowski | UCIBzmtDQ1SrE0r7jtWbiTNw |
| cdf73155-... | Studio Prawy_PL | UCoH2G9By4OX3kcLsc8lHgDw |
| 776a3a65-... | Prawy TV | UCNXh5eIlMVxnUBpTMKUp4CA |

### youtube_channels OAuth status (15.09.2026)
- VeriNarrMundo: `invalid_grant` (wygasły token)
- Tomasz Brzozowski: OK
- Studio Prawy\_PL: OK
- Prawy TV: OK

## 14. YT Description — poprawna metoda (odkryto 15.09.2026)

### Problem z publish-description
`POST /v1/youtube/publish-description` sprawdza czy video należy do podanego kanału.
Filmy na kanałach Prawy zarządzanych przez konto Tomasz Brzozowski zwracają
`"error: channel not found or access denied"` dla wszystkich UUID w VSE.

### Właściwa metoda: yt_desc_fix.py w kontenerze
```bash
# Skopiuj skrypt do kontenera i uruchom
docker cp /tmp/yt_desc_fix.py vse-api:/app/yt_desc_fix.py
docker exec -w /app vse-api python3 yt_desc_fix.py
```

Skrypt `agents/vse-worker/scripts/yt_desc_fix.py`:
- Ładuje token Tomasz Brzozowski z bazy przez `_build_credentials(ch).refresh(Request())`
- Pobiera schema_data z `transcript_jobs WHERE video_url LIKE '%{yt_id}%'`
- Buduje opis z pól: `lead` + `chapters` (lista dictów) + `tags` + link WP
- Aktualizuje przez `youtube.videos().update()` (NIE przez publish-description)

### Budowanie opisu YT z transcript_jobs.schema_data
```python
# lead -> opis główny
lead = schema.get("lead", "")

# chapters -> lista dictów {"time": "00:00", "title": "..."}
raw_chapters = schema.get("chapters", [])
chapter_lines = [f"{c.get('time','')} {c.get('title','')}".strip() for c in raw_chapters if isinstance(c, dict)]
chapters_str = "\n".join(chapter_lines)

# tags -> lista stringów
tags = schema.get("tags", [])
hashtags_str = " ".join(f"#{t}" if not t.startswith("#") else t for t in tags)

desc = f"{lead}\n\n{chapters_str}\n\n{hashtags_str}\n\nCzytaj wiecej: {wp_url}"
```

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

*[media-strateg-01 | media-dispatch 29.08.2026 — init]*  
*[Supervisor 01 | sonic-void 29.08.2026 — pułapki live]*  
*[Supervisor 01 | sonic-void 30.08.2026 — architektura audio vs YT pipeline, OAuth rotation, retrofitting thumbnails]*  
*[media-strateg | media-dispatch 30.08.2026 — pułapki 11-14: llm_provider=claude, publication_type=full_analysis, portal_id UUID, YT token przez SSH _build_credentials]*  
*[media-dev-12 | media-dispatch 31.08.2026 — sekcja Short Machine API (/v1/shorts/describe) na produkcji, pułapki 15-18]*

---

## Konto VSE — zawsze tobroz@gmail.com

- USER_ID: `4b97ab0c-98ee-46c6-9be8-d86adc4cb38a`
- Email: `tobroz@gmail.com`
- OAuth: podpięte kanały Studio Prawy_PL (`UCoH2G9By4OX3kcLsc8lHgDw`) i Prawy Biblijny (`UCNXh5eIlMVxnUBpTMKUp4CA`)
- Zakaz używania innych kont do operacji VSE

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
