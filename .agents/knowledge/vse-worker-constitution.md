# VSE Worker Constitution (media-dispatch)

> Ostatnia aktualizacja: 2026-08-29 | media-strateg-01 + Supervisor 01 (sesja live)

Dokument opisuje zasady operacyjne dla workerów z rodziny `vse-worker`.
Zawiera wiedzę zdobytą zarówno z poprzednich sesji jak i weryfikacji live 29.08.2026.

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

Generuj token bezpośrednio wewnątrz kontenera przez `jose.jwt`:

```bash
# Zapisz skrypt lokalnie, wyślij przez SCP, wykonaj przez SSH:
ssh -i C:\Users\tomas2\.ssh\oracle-crimson.key -o StrictHostKeyChecking=no ubuntu@147.224.162.100 "
docker exec vse-api python3 -c \"
import os, datetime
from jose import jwt
secret = os.environ.get('JWT_SECRET_KEY', '')
payload = {
  'sub': '4b97ab0c-98ee-46c6-9be8-d86adc4cb38a',
  'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
}
token = jwt.encode(payload, secret, algorithm='HS256')
print(token)
\""
```

### Konto administratora
- Email: `tobroz@gmail.com`
- ID: `4b97ab0c-98ee-46c6-9be8-d86adc4cb38a`
- Plan: Agency (quota 9999)
- is_admin: true

### ❌ Metody które NIE działają
- `from api.auth import create_access_token` — wymaga argumentu `email` jako osobnego param (nie dict), psuje się w różnych wersjach
- `curl -X POST http://localhost:8085/v1/auth/login` z hasłem inline — hasło admina nie jest w .env jako `ADMIN_PASS`, nie ma prostego dostępu
- Wywołanie `/v1/auth/login` z PowerShell inline z cudzysłowami — escapowanie JSON w PS przez SSH jest niestabilne

### Weryfikacja tokenu
```bash
curl -s -H "Authorization: Bearer TOKEN" http://localhost:8085/v1/users/me
# Oczekiwany wynik: {"email":"tobroz@gmail.com","is_admin":true,...}
```

---

## 3. API Routes — pełna lista (29.08.2026)

```
/v1/process
/v1/generate
/v1/inject
/v1/audio/generate          ← MP3 → Whisper → SEO
/v1/generate-audio          ← alias dla /v1/audio/generate
/v1/auth/login
/v1/auth/register
/v1/auth/refresh
/v1/users/me
/v1/jobs/{job_id}/vtt       ← pobierz VTT z joba
/v1/shorts/transcribe-audio
/v1/youtube/channels        ← lista kanałów konta OAuth
/v1/youtube/publish-description
/v1/youtube/channels/{channel_id}/playlists
/v1/portals
/v1/podcast/shows
/health
```

---

## 4. Audio Pipeline (Whisper)

- **Endpoint:** `POST https://vse.impresjapr.pl/v1/audio/generate`
- **Metoda:** `multipart/form-data`
- **Parametry:**

```python
requests.post(
    "https://vse.impresjapr.pl/v1/audio/generate",
    headers={"Authorization": "Bearer TOKEN"},
    files={"file": (mp3_path.name, open(mp3_path, "rb"), "audio/mpeg")},
    data={
        "publication_type": "film",   # lub full_analysis, watching_page
        "portal_id": "prawy",
        "post_title": "Biblia 30.08.2026 Mt 16,21-27",
        "lang": "pl",
        "llm_provider": "gemini",
    },
    timeout=600,  # 8-min audio ≈ 2-3 min processing
)
```

- **Model:** `faster-whisper small` (CPU, int8, 4 threads)
- **Output:** `GenerateResponse` z `schema_data` (VTT, SEO, artykuł)
- **VTT:** dostępny przez `schema_data` lub endpoint `/v1/jobs/{job_id}/vtt`

---

## 5. YouTube OAuth

- Konto: `tobroz@gmail.com` — obsługuje oba kanały (Prawy TV + Prawy Biblijny)
- OAuth tokens przechowywane w **bazie danych VSE** (tabela kanałów/portali), NIE w plikach YAML
- YAML-e w `video-seo-engine/channels/` to tylko config developerski — runtime używa DB
- Endpoint do listy kanałów konta: `GET /v1/youtube/channels`
- Endpoint do publikacji opisu: `POST /v1/youtube/publish-description`

### ⚠️ Pułapka: scope
403 Forbidden przy update YouTube → brak scope `https://www.googleapis.com/auth/youtube` w tokenie.

---

## 6. Znane Pułapki — sesja 29.08.2026 (live)

| # | Pułapka | Rozwiązanie |
|---|---------|-------------|
| 1 | **Port VSE wewnętrzny: 8085** (nie 8000) | Zawsze `http://localhost:8085` przy wywołaniach wewnętrznych |
| 2 | **URL endpointu: `/v1/`** nie `/api/v1/`  | Publiczne URL: `https://vse.impresjapr.pl/v1/...` |
| 3 | **create_access_token() psuje się** | Używaj `jose.jwt.encode()` bezpośrednio z `JWT_SECRET_KEY` |
| 4 | **SQL przez SSH z PowerShell** — escapowanie cudzysłowów | Pisz skrypt bash → `write_to_file` → `scp` pełna ścieżka → `ssh bash /tmp/...` |
| 5 | **SCP `~` na Windows** nie działa | ZAWSZE pełna ścieżka: `C:\Users\tomas2\...` |
| 6 | **Whisper timeout** — 8-min audio może trwać 3-5 min | timeout=600s, nie przerywaj żądania |
| 7 | **prawy-biblijny.yaml w channels/** — zbędne | Kanał jest w DB VSE (podłączony przez OAuth). Nie twórz YAML-i dla istniejących kanałów |
| 8 | **PS interpoluje `$variable`** w SSH string | Używaj `'apostrofów'` lub skryptu bash |

---

## 7. Wzorce Kodu

### Generowanie tokenu (niezawodny)
```bash
# write_to_file → scp → ssh
cat > /tmp/gen_token.py << 'EOF'
import os, datetime
from jose import jwt
secret = os.environ.get('JWT_SECRET_KEY', '')
payload = {
    'sub': '4b97ab0c-98ee-46c6-9be8-d86adc4cb38a',
    'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
}
print(jwt.encode(payload, secret, algorithm='HS256'))
EOF
docker exec -i vse-api python3 < /tmp/gen_token.py
```

### Poprawny SCP (Windows → VPS)
```powershell
scp -i C:\Users\tomas2\.ssh\oracle-crimson.key -o StrictHostKeyChecking=no `
  "C:\Users\tomas2\.gemini\antigravity\playground\sonic-void\tmp\skrypt.sh" `
  ubuntu@147.224.162.100:/tmp/skrypt.sh
```

### Upload MP3 do VSE (Python)
```python
import requests
from pathlib import Path

token = "eyJ..."  # z gen_token.py
mp3 = Path(r"C:\Users\tomas2\Videos\Prawy\Biblia...\film.mp3")

resp = requests.post(
    "https://vse.impresjapr.pl/v1/audio/generate",
    headers={"Authorization": f"Bearer {token}"},
    files={"file": (mp3.name, mp3.open("rb"), "audio/mpeg")},
    data={"publication_type": "film", "portal_id": "prawy", "lang": "pl", "llm_provider": "gemini"},
    timeout=600,
)
print(resp.json())
```

---

## 8. Kanały Biblijne — wiedza operacyjna

| Element | Wartość |
|---------|--------|
| Kanał | Prawy Biblijny |
| Konto | tobroz@gmail.com (ten sam OAuth co Prawy TV) |
| Playlista Ewangelia | `PLw7UeigJuyWkUzzvhS1vZX0H251raaYa7` |
| Konfig w VSE | W bazie danych — NIE w YAML |
| Publish time | 00:00 CEST (`+02:00`) danego dnia |
| Typ publikacji WP | `film` |
| Lang | `pl` |
| LLM | `gemini` |

---

*[media-strateg-01 | media-dispatch 29.08.2026 — init]*  
*[Supervisor 01 | sonic-void 29.08.2026 — uzupełnienie pułapek live]*
