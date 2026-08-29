# VSE Worker Constitution (media-dispatch)

> Ostatnia aktualizacja: 2026-08-30 | Supervisor 01 (sesja live + analiza architektoniczna)

Dokument opisuje zasady operacyjne dla workerów z rodziny `vse-worker`.
Zawiera wiedzę zdobytą zarówno z poprzednich sesji jak i weryfikacji live 29-30.08.2026.

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

## 3. API Routes — kluczowe (29.08.2026)

```
/v1/audio/generate          ← MP3 → Whisper → SEO (bez thumbnail!)
/v1/generate                ← YouTube URL → SEO (z thumbnail, VideoObject schema)
/v1/inject                  ← wstrzyknij schema do WP
/v1/jobs/{job_id}/vtt       ← pobierz VTT z joba
/v1/youtube/channels        ← lista kanałów konta OAuth
/v1/youtube/oauth/login     ← link do reautoryzacji OAuth
/v1/youtube/publish-description  ← update opisu na YT
/v1/youtube/channels/{channel_id}/playlists
/v1/portals                 ← config portali WP (credentials)
/health
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

### ✅ Prawidłowy flow dla kanału bez auto-napisów (np. YT nie rozpoznał języka)

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

```python
resp = requests.post(
    "https://vse.impresjapr.pl/v1/audio/generate",
    headers={"Authorization": "Bearer TOKEN"},
    files={"file": (mp3_path.name, open(mp3_path, "rb"), "audio/mpeg")},
    data={"lang": "pl", "llm_provider": "gemini"},
    timeout=600,
)
vtt_text = resp.json()["schema_data"].get("vtt") or resp.json()["schema_data"].get("transcript")
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
NIE próbuj naprawiać przez kod. Zgroś bloker do Supervisora.
User musi otworzyć: `https://vse.impresjapr.pl/v1/youtube/oauth/login` i zatwierdzić dostęp.

---

## 7. Znane Pułapki — sesja 29-30.08.2026 (live)

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

---

## 8. Wzorce Kodu

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

---

## 9. Kanały Biblijne — wiedza operacyjna

| Element | Wartość |
|---------|--------|
| Kanał | Prawy Biblijny |
| Konto | tobroz@gmail.com (ten sam OAuth co Prawy TV) |
| Playlista Ewangelia | `PLw7UeigJuyWkUzzvhS1vZX0H251raaYa7` |
| Typ publikacji WP | `film` |
| Lang | `pl` | LLM | `gemini` |
| Publish time | 00:00 CEST (`+02:00`) danego dnia |
| Pliki lokalne | `C:\Users\tomas2\Videos\Prawy\Biblia [data]\` (MP3 + MP4) |
| Thumbnails lokalne | `D:\Biblioteki\prawy video\Biblia\Biblia [data]\` |

---

*[media-strateg-01 | media-dispatch 29.08.2026 — init]*  
*[Supervisor 01 | sonic-void 29.08.2026 — pułapki live]*  
*[Supervisor 01 | sonic-void 30.08.2026 — architektura audio vs YT pipeline, OAuth rotation, retrofitting thumbnails]*
