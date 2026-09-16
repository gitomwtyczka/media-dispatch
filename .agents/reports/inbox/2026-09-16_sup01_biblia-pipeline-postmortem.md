# Post-mortem analiza sesji Biblia Pipeline 16.09.2026

**Od:** Supervisor 01 | sonic-void
**Callsign:** [post-mortem-analyst | sonic-void 16.09.2026]

## 1. CO ZADZIALAŁO (single source of truth)
Ścieżka, która z powodzeniem utworzyła wpisy na prawy.pl (5/5 sukces):
- **VSE Generate (`/v1/generate`)**:
  - `video_url`: `https://www.youtube.com/watch?v={yt_id}` (Należy używać URL YouTube, nie pliku audio, aby generował się thumbnail i embed)
  - `portal_id`: `"2b047d7d-15a1-4d2f-8463-f89c2275bb73"` (Używamy bezwzględnie UUID, alias 'prawy' powodował błędy)
  - `llm_provider`: `"claude"` (Nie "gemini", gdyż brakuje klucza na VPS)
  - `lang`: `"pl"`
  - `publication_type`: `"full_analysis"`
- **VSE Inject (`/v1/inject`)**:
  - Przekazujemy `schema_data` z `/v1/generate`
  - `publish_date`: Odpowiednia data (np. `"2026-09-16T00:00:01+02:00"`)
  - `status`: `"future"` (dla zaplanowanych) lub `"publish"`
  - `portal_id`: `"2b047d7d-15a1-4d2f-8463-f89c2275bb73"`
- **Autoryzacja VSE (JWT)**:
  - Header: `Authorization: Bearer {token}`
  - Generowanie: Algorytm HS256, `sub="4b97ab0c-98ee-46c6-9be8-d86adc4cb38a"`, `email="tobroz@gmail.com"`, `JWT_SECRET` pobierany z `.env` na serwerze.
- **Wyniki (WP Post IDs)**:
  - `AMd9euz4dvM` → wp=126371 (2026-09-15)
  - `vNoDWfjXHIU` → wp=126376 (2026-09-16)
  - `2IB0AXXhagk` → wp=126381 (2026-09-17)
  - `-z8X2PEuW34` → wp=126386 (2026-09-18)
  - `0rGHXiSVM-4` → wp=126391 (2026-09-19)

## 2. CO NIE ZADZIAŁAŁO I DLACZEGO
- **YouTube 403 Forbidden**: Raw `access_token` wyciągnięty wprost z bazy danych wygasa po około godzinie. Użycie go w requestach (np. `requests.put` czy API klienta YouTube) rzucało błędem autoryzacji 403 Forbidden.
- **Worker anti-pattern**: Zamiast skupić się na wykonaniu przygotowanego skryptu (uruchomienie go w odpowiednim kontenerze i zebranie wyników), workerzy zaczęli zagłębiać się w kod (np. parsowanie/czytanie kodu VSE za pomocą grep/sed). Przez to tracili kontekst i nie byli w stanie dokończyć właściwego prostego zadania wykonania kodu i zaktualizowania API.
- **Błędne nazwy kolumn modeli**: Próba użycia `ch.channel_id` czy `ch.client_id` zamiast prawidłowego `ch.youtube_channel_id` rzucała `AttributeError`.

## 3. YOUTUBE — OTWARTA KWESTIA / STATUS
- **Aktualny status**: Worker `cb521820` ostatecznie **zakończył się sukcesem**. Rzeczywisty wynik z bezpośredniej weryfikacji API (`videos().list`) potwierdza, że filmy zostały opublikowane / zaplanowane:
  - `AMd9euz4dvM` | public | None
  - `vNoDWfjXHIU` | public | None
  - `2IB0AXXhagk` | private | 2026-09-17T05:00:01Z (scheduled)
  - `-z8X2PEuW34` | private | 2026-09-18T05:00:01Z (scheduled)
  - `0rGHXiSVM-4` | private | 2026-09-19T05:00:01Z (scheduled)
- **Co próbowano (zanim zadziałało)**: Próbowano aktualizować opisy i status używając bezpośrednio `requests.put` z raw tokenem, a potem budując poświadczenia wewn. skryptami. Worker podjął próbę wylistowania playlisty za pomocą _build_credentials, co początkowo sprawiało problemy przez nieznajomość modelu, ale ostatecznie pipeline zadziałał prawidłowo.
- **Co powinno działać na przyszłość**: Najlepiej użyć endpointu VSE `POST /v1/youtube/publish-description`, autoryzując się za pomocą VSE JWT (z konta tobroz@gmail.com). Endpoint automatycznie obsłuży uwierzytelnienie w YouTube API za pomocą mechanizmów VSE, dbając o tokeny (odświeżanie) na podstawie zintegrowanych sesji. Alternatywą jest poprawne użycie `api.core.youtube_publish._build_credentials` (tak jak zrobiono to w ostatecznej udanej próbie).

## 4. DISPATCH TEMPLATE NA PRZYSZŁOŚĆ
**Lokalizacja pipeline'ów**: Repozytorium `media-dispatch`, ścieżka `agents/vse-worker/scripts/`.
- `biblia_full_pipeline.py`: Prawidłowy pełny flow (audio -> transkrypcja -> captions -> SEO yt -> WP). Używać dla nowych filmów.
- `biblia_backlog_pipeline.py`: Poprawiona wersja skryptu obsługującego VSE JWT i `_build_credentials`. Wykorzystuje UUID dla portalu i prawidłowy `llm_provider`. Z niego należy korzystać dla aktualizacji zaległości.

**Szablon Dispatchu dla agentów biblijnych**:
```markdown
# DISPATCH — Biblia Pipeline

**Zasada:** TYLKO WYKONAJ ZADANE KROKI, NIE CZYTAJ I NIE EKSPLORUJ KODU ZRODŁOWEGO VSE. Masz gotowy skrypt/polecenia.

Skrypt do uruchomienia to `biblia_full_pipeline.py` (lub w razie backlogu `biblia_backlog_pipeline.py`), dostępny w repozytorium `media-dispatch` pod `agents/vse-worker/scripts/`.
1. Zapisz skrypt do `/tmp/`.
2. Prześlij przez SCP do kontenera/serwera.
3. Wykonaj.

## ⚠️ ZNANE PUŁAPKI biblia-worker (przeczytaj ZANIM zaczniesz)
1. SCP na Windows: NIGDY nie używaj `~` w ścieżce lokalnej. Zawsze podawaj pełną ścieżkę (np. `C:\Users\tomas2\.ssh\...`).
2. Skrypty VSE z zależnościami (np. requests, jose, google-api-python-client) uruchamiaj ZAWSZE wewnątrz kontenera: `docker exec vse-api python3 /app/<skrypt.py>`.
3. Wywoływanie poleceń SSH w PowerShellu: Nie łącz komend przy użyciu `&&`. Wykonuj krok po kroku.
4. Token YT (`access_token`) wygasa! Nie wklejaj go jako statyczny string, zawsze korzystaj z VSE API `/v1/youtube/publish-description` (używając VSE JWT) lub wykorzystaj wbudowany moduł VSE `api.core.youtube_publish._build_credentials`.
5. Portal ID to ZAWSZE UUID (`2b047d7d-15a1-4d2f-8463-f89c2275bb73`), nie używaj aliasów stringowych (np. "prawy"). LLM Provider to `claude`.
6. Channel ID: Prawidłowy kanał dla edycji materiałów Biblii to **Prawy TV** (`UCNXh5eIlMVxnUBpTMKUp4CA`), NIE Studio Prawy_PL (`UCoH2G9By4OX3kcLsc8lHgDw`). Użycie złego kanału przy aktualizacjach zablokuje wykonanie kodu.
```

## 5. ZNANE PUŁAPKI (gotowy blok do wklejenia w dispatche)
```markdown
## ⚠️ ZNANE PUŁAPKI biblia-worker
1. **SCP Windows**: NIGDY `~` w lokalnej ścieżce. Zawsze pełne ścieżki Windows.
2. **Uruchamianie**: Skrypt uruchamiaj przez `docker exec vse-api python3 /app/<skrypt.py>`, aby zagwarantować obecność zależności.
3. **SSH w PS**: Jeden krok na raz przez SSH — nie łącz komend przez `&&`.
4. **Tokeny YouTube**: Raw `access_token` wygasa po 1h. Używaj VSE endpointu `/v1/youtube/publish-description` z JWT (VSE ogarnie YT) lub metody `_build_credentials()` z wnętrza kontenera.
5. **Parametry VSE**: `portal_id` to UUID (`2b047d7d-15a1-4d2f-8463-f89c2275bb73`), a `llm_provider` to `claude` (brak gemini na VPS).
6. **Channel ID**: Prawidłowy kanał dla Biblii to **Prawy TV** (`UCNXh5eIlMVxnUBpTMKUp4CA`). NIE używaj `UCoH2G9By4OX3kcLsc8lHgDw` (Studio Prawy_PL).
```

---

## ⚠️ MINY — Biblia Worker (aktualizacja 16.09.2026, sesja post-mortem)

### MINA 1 — VSE `/v1/inject` tworzy posty jako `draft`
**Objaw:** Post stworzony przez VSE ma status `draft` nawet przy `status=future/publish` w payload.
**Przyczyna:** VSE ignoruje pole `status` przy tworzeniu nowego posta (bez `wp_post_id`) — zawsze draft.
**Fix obowiązkowy po każdym `/v1/inject`:**
```bash
# Past/today:
docker exec prawy-wordpress wp post update {wp_id} \
  --post_status=publish --post_date='YYYY-MM-DD 00:00:01' \
  --post_date_gmt='YYYY-MM-DD 22:00:01' --edit_date=true --allow-root
# Future:
docker exec prawy-wordpress wp post update {wp_id} \
  --post_status=future --post_date='YYYY-MM-DD 00:00:01' \
  --post_date_gmt='YYYY-MM-DD 22:00:01' --edit_date=true --allow-root
```

### MINA 2 — Błędny YT channel_id (Studio Prawy_PL vs Prawy TV)
**Objaw:** 403 Forbidden przy `videos().update()` mimo ważnego tokenu.
**Przyczyna:** Filmy Biblii należą do kanału `Prawy TV`, nie `Studio Prawy_PL`.
**Poprawne ID:**
```
Prawy TV (do edycji filmów Biblia): UCNXh5eIlMVxnUBpTMKUp4CA  ✓
Studio Prawy_PL (błędny dla Biblii): UCoH2G9By4OX3kcLsc8lHgDw  ✗
```

### MINA 3 — Raw YT access token z bazy wygasa po ~1h
**Objaw:** 403 Forbidden przy YouTube API nawet z tokenem z `youtube_channels` tabeli.
**Przyczyna:** Google access token żyje ok. 1 godziny. Token z DB jest często przeterminowany.
**Fix — refresh wewnątrz `vse-api` kontenera:**
```python
# Uruchamiaj wyłącznie przez: docker exec vse-api python3 /app/skrypt.py
from api.core.youtube_publish import _build_credentials
creds = _build_credentials(channel_obj)  # channel_obj z DB
creds.refresh(Request())  # odświeża access_token automatycznie
# Następnie: build('youtube', 'v3', credentials=creds)
```
Alternatywnie: użyj VSE endpointu `/v1/youtube/publish-description` z JWT VSE — VSE odwięża token wewnętrznie.

### MINA 4 — `/v1/youtube/publish-description` wymaga `schema_data`
**Objaw:** 422 Unprocessable Entity przy wywołaniu z payload `{video_id, channel_ids}`.
**Przyczyna:** Endpoint wymaga pełnego `schema_data` z `/v1/generate`.
**Poprawny payload:** Należy najpierw wywołać `/v1/generate` i przekazać `schema_data` do publish-description.

### MINA 5 — Worker anti-pattern: eksploracja zamiast wykonania
**Objaw:** Worker dostaje YT token, ma gotowy skrypt, ale zamiast go uruchomić zaczyna czytać kod źródłowy (grep, sed na plikach .py).
**Przyczyna:** Zbyt dużo swobody w dispatchu + brak explicit zakazu eksploracji.
**Fix — obowiązkowe frazy w każdym dispatchu do workerów:**
```
NIE czytaj kodu źródłowego. Nie używaj grep/sed na plikach projektu.
Tylko X kroków. Nic więcej.
```

---

## ✅ POPRAWNY FLOW — Biblia Worker (single source of truth)

### Wymagania wstępne
```python
VSE_BASE   = "https://vse.impresjapr.pl"
JWT_SECRET = "9264f609..."  # z /home/ubuntu/video-seo-engine/.env na VPS
USER_ID    = "4b97ab0c-98ee-46c6-9be8-d86adc4cb38a"  # tobroz@gmail.com
PORTAL_ID  = "2b047d7d-15a1-4d2f-8463-f89c2275bb73"  # UUID! nie 'prawy'
YT_CHANNEL = "UCNXh5eIlMVxnUBpTMKUp4CA"              # Prawy TV
LLM        = "claude"                                  # NIE gemini
```

### Krok 1 — VSE Generate
```python
POST /v1/generate
{
  "video_url": "https://www.youtube.com/watch?v={yt_id}",
  "portal_id": PORTAL_ID,
  "publication_type": "full_analysis",
  "lang": "pl",
  "llm_provider": "claude"
}
# → zwraca schema_data
```

### Krok 2 — VSE Inject (WP post)
```python
POST /v1/inject
{
  "video_url": "https://www.youtube.com/watch?v={yt_id}",  # WYMAGANE
  "schema_data": schema_data,
  "portal_id": PORTAL_ID,
  "publish_date": "2026-09-17T00:00:01+02:00",
  "status": "future"  # lub "publish" — VSE ignoruje, zawsze draft!
}
# → zwraca wp_post_id
```

### Krok 3 — WP-CLI fix (OBOWIĄZKOWY po inject)
```bash
# Na VPS przez SSH, OSOBNE komendy:
docker exec prawy-wordpress wp post update {wp_id} \
  --post_status=future \
  --post_date='2026-09-17 00:00:01' \
  --post_date_gmt='2026-09-16 22:00:01' \
  --edit_date=true --allow-root
docker exec prawy-wordpress wp post term add {wp_id} podcast_show prawy-biblijny --allow-root
docker exec prawy-wordpress wp post meta update {wp_id} podcast_youtube_url 'https://www.youtube.com/watch?v={yt_id}' --allow-root
docker exec prawy-wordpress wp cache flush --allow-root
```

### Krok 4 — YouTube update (przez vse-api container)
```python
# Uruchom przez: docker exec vse-api python3 /app/skrypt.py
# skrypt musi importować wewnętrzne moduły VSE
from api.core.youtube_publish import _build_credentials
from api.models.youtube_channel import YouTubeChannel
# ... refresh token, build service, videos().update()
# channel_id w ORM to pole: youtube_channel_id (nie channel_id!)
```

### Krok 5 — YouTube opis przez VSE (po refresh tokenu)
```python
POST /v1/youtube/publish-description
{
  "video_id": yt_id,
  "schema_data": schema_data,  # z kroku 1!
  "channel_ids": [YT_CHANNEL]
}
```

### Autoryzacja VSE (JWT)
```python
import jwt as pyjwt
from datetime import datetime, timezone, timedelta
exp = datetime.now(timezone.utc) + timedelta(hours=24)
token = pyjwt.encode({"sub": USER_ID, "email": "tobroz@gmail.com", "exp": exp},
                     JWT_SECRET, algorithm="HS256")
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
```

*[post-mortem-analyst update | sonic-void 16.09.2026 23:26]*
