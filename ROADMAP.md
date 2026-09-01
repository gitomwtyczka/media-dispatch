# media-dispatch - ROADMAP v1.3

## Wizja

media-dispatch to Content Operating System - system agentow AI
ktory bez recznej pracy zbiera tematy, produkuje tresci i dystrybuuje
je na wiele platform jednoczesnie.

## Architektura 4-warstwowa

[Wywiad] -> [Redaktor Naczelny] -> [Producenci] -> [Platformy]

## Fazy

### FAZA 0: Fundament (teraz)
- Repo + workspace + AGENTS.md
- Migracja batch_vse_pipeline.py jako agents/vse-worker/ (oraz prawy-studio-worker)
- Wspolny API client shared/api_clients/

### FAZA 1: pressAI Worker
- Wejscia: email, URL, tekst
- Wyjscie: artykul na portal WordPress
- Mapowanie API pressAI

## Architektura dwutorowa (01.09.2026)

### Ścieżka A — Editorial (główna)
```
Intelligence (feed-crawler + Gmail P0 + GeoRelevance)
    ↓
Sheets Kandydaci (kolejka redakcyjna)
    ↓ [Redaktor Naczelny AI zatwierdza]
PressAI Klastry + Planowanie
    ↓
PressAI Generowanie (phrases + AI) + Quality
    ↓
WP Draft → [ręczna publikacja]
```

### Ścieżka B — Auto-batch (boczna / eksperymentalna)
```
Intelligence (feed-crawler + Gmail P0 + GeoRelevance)
    ↓
Auto-generate via PressAI API (kurier365-worker)
    ↓
PressAI historia → [user dodaje obrazki] → WP Draft
```
*Używana dla: treści szybkich, kandydatów P2-P3, eksperymenty*
*Kandydaci P0 (Gmail) zawsze przez Ścieżekę A*

### Content Radar — brakująca integracja
- **Aktualny status:** autonomiczny projekt (radar.impresjapr.pl) BEZ integracji z PressAI
- **Potencjał:** wskazuje trendy social media → powinna informować wybory klastrów i fraz w PressAI
- **Planowana integracja:** Faza 3 — Content Radar → PressAI phrase selection + cluster prioritization

### FAZA 1b: shorts-agent + Short Machine Integration (API gotowe na produkcji od 31.08.2026. Implementacja workers: Q1 09.2026)
- Skanowanie opublikowanych shortów na kanale YouTube Studio Prawy_PL (`UCoH2G9By4OX3kcLsc8lHgDw`)
- Audyt jakości SEO i automatyczne generowanie brakujących opisów przez **Short Machine** (`POST /v1/shorts/describe`)
- Weryfikacja brakujących opisów SM: `description.length < 50` lub tytuł = nazwa pliku mp4
- Aktualizacja snippetu wideo (zoptymalizowany tytuł max 45 zn bez #Shorts, opis 150-350 zn bez URL, max 5 hashtagów bez #Shorts, przypięty komentarz APV) przez YouTube Data API v3
- Silnik harmonogramowania publikacji (`shared/schedules/shorts_schedule.json`): ~6 shortów/film, rozkład na 2-6 dni, peak slots: `07:00`, `12:00`, `18:00`, `21:00` CEST
- Integracja ze strukturą katalogów `C:\VSE\Shorts\[Film]_[date]\` (`*_raw.mp4` vs `*_gotowy.mp4`)

### FAZA 1c: prawy-youtube-worker (Autonomiczny worker YT Studio Prawy_PL)
- `prawy-youtube-worker v1.0 skeleton — 01.09.2026`
- Integracja `YouTubeChannelSource` z `WorkerBase`
- Pipeline VSE: `POST /v1/generate` -> `POST /v1/inject` (draft) -> `POST /v1/shorts/candidates`
- Bezpieczeństwo i Human-in-the-Loop: WP=draft, YT=unlisted
- Wzbogacanie trendami z Content Radar (`radar.impresjapr.pl`)

### FAZA 2: Pipeline publikacji Kurier365 + Gmail Stream (w toku)

**✅ MVP v0.1 skeleton + źródła aktywne (31.08–01.09.2026) — media-dev-architect, media-dev-30, media-dev-31**

Zaimplementowano rozszerzalną architekturę Plugin-based Workers:

#### agents/base/ — bazowa architektura workerów
- `worker_base.py` — WorkerBase, SourcePlugin, TrendSignal, ContentCandidate
- `sources/gmail_source.py` — GmailSource (PressAI Gmail API, tobroz@gmail.com, priorytetowi nadawcy P0)
- `sources/feed_crawler_source.py` — FeedCrawlerSource (13k+ feedów RSS, crawler.impresjapr.pl, działy tematyczne)
- `sources/newseria_source.py` — NewseriaSource z Eco-Bias Gate
- `sources/youtube_channel_source.py` — YouTubeChannelSource dla monitorowania kanałów YT
- `trend_signals/geo_relevance_signal.py` — GeoRelevanceSignal (priorytetyzacja PL/EU/US-biznes)
- `trend_signals/content_radar_signal.py` — **LIVE** integracja z radar.impresjapr.pl
- `trend_signals/google_trends_signal.py` — fallback placeholder

#### agents/kurier365-worker/ — pierwsza instancja WorkerBase
- `worker.py` — Kurier365Worker (kurier365.pl)
  - Sources: Gmail (Rudiński, Bińczyk, WEI, Biały Kruk, Juchniewicz, Bolek, Zabka, Maxmedia, Gryżewski, Kalinowska, Art-Media, Fundacja XBW), FeedCrawler (UOKiK, PAP, Nauka, ISBNews, Nauki ścisłe, Geopolityka), Newseria
  - Trend Signals: GeoRelevanceSignal (LIVE), ContentRadarSignal (LIVE gdy CONTENT_RADAR_JWT), Google/Social (fallback)
  - CLI: --health, --run, --top N, --sheets, --json

#### agents/prawy-youtube-worker/ — dedykowany worker kanału YT Studio Prawy_PL
- `worker.py` — PrawyYouTubeWorker (prawy.pl)
  - Sources: YouTubeChannelSource (`UCoH2G9By4OX3kcLsc8lHgDw`)
  - Trend Signals: ContentRadarSignal (LIVE gdy CONTENT_RADAR_JWT)
  - Pipeline VSE: generate SEO -> inject WP draft -> shorts candidates -> editorial review
  - CLI: --health, --video-id, --run

#### Następne kroki w Fazie 2 (Pipeline publikacji):
- **`pressai-publisher-integration`** — połączenie selekcji kandydatów z generowaniem i auto-draftem w WordPress dla kurier365.pl (`POST /api/editor/generate` + `POST /api/publisher/publish/{id}`)
- **`newseria-connector`** — scraping sesyjny Newseria
- **`biznesciti-worker`** — instancja WorkerBase dla biznesciti.com
- **`pressai-worker`** — rozszerzenie o playbooki per portal

### FAZA 3: Discord Editorial Center (Future) `[odroczone 01.09.2026 — priorytet: uruchomienie publikacji]`
- Interaktywne centrum redakcyjne na Discordzie
- FastAPI Interactions endpoint (`/api/v1/discord/interactions`) + Discord Webhooks + Embeds z przyciskami (Action Row: Akceptuj, Odrzuć, Odrocz D+1, Odrocz D+7, Uwagi przez Modal)
- Dual-channel workflow: `#editorial-propozycje` + `#editorial-priority`
- Komunikacja dwukierunkowa: akceptacja tematu przez redaktora wyzwala automatyczny pipeline generacji i publikacji

### FAZA 4: Content Radar Worker
- **GOTOWE na produkcji (31.08.2026)** — radar.impresjapr.pl
- Google Trends API (pytrends, geo=PL, 7d)
- Social media trending (Twitter/X, TikTok, Instagram, YouTube, Reddit, FB, LinkedIn)
- APScheduler co 15 min
- Viral Score: `views*0.1 + likes*1.0 + shares*3.0 + comments*2.0 + GT_boost`
- Integracja: `ContentRadarSignal` w `agents/base/trend_signals/`
- Endpoint: `GET /api/v1/trending/global` (wymaga JWT + plan Pro)

### FAZA 5: Redaktor Naczelny (Zaawansowana Meta-Orkiestracja)
- Syntetyzuje dane z Intelligence
- Proponuje tematy per portal
- Po GO usera -> dispatch do producentow
- Raport tygodniowy: editorial/YYYY-WW_propozycje.md

### FAZA 6: Multi-platform Distribution
- YouTube worker: upload + scheduling
- TikTok worker: shorty z VSE
- Telegram worker: bot API (dystrybucja kanałowa)

### FAZA 6b: TikTok Upload (Gotowe Shorty _gotowy.mp4)
- Integracja `tiktok-worker` z lokalną bazą wideo `C:\VSE\Shorts\`
- Quality Gate: publikacja wyłącznie plików ze statusem/sufiksem `*_gotowy.mp4` po akceptacji człowieka
- Wykorzystanie pakietów SEO (hook, opis, hashtagi) wygenerowanych przez Short Machine
- Realizacja publikacji zgodnie z harmonogramem `shorts_schedule.json`

## Standardy techniczne

### Agent interface
Kazdy worker musi implementowac:
- health_check() -> bool
- process(task: Task) -> Result
- get_status() -> WorkerStatus

### Task schema
```json
{
  "task_id": "uuid",
  "type": "vse|pressai|shorts|publish|tiktok|gmail|feed_crawler",
  "portal_id": "prawy|kurier365|biznesciti",
  "input": {},
  "priority": 1,
  "scheduled_at": "ISO timestamp",
  "created_by": "redaktor-naczelny|shorts-agent|user"
}
```

## Priorytety MVP
1. VSE worker / prawy-studio-worker / prawy-youtube-worker v1.0 - zaimplementowany (01.09.2026)
2. shorts-agent + Short Machine - API gotowe na produkcji od 31.08.2026 (`/v1/shorts/describe`), implementacja workers: Q1 09.2026
3. pressAI worker - kluczowy dla skali
4. **kurier365-worker + Gmail Stream (Faza 2)** — aktywne zbieranie kandydatów, priorytet: uruchomienie publikacji (01.09.2026)
5. Content Radar (radar.impresjapr.pl) - LIVE na produkcji (31.08.2026)
6. **Discord Editorial Center (Faza 3 Future)** — odroczone na rzecz uruchomienia publikacji (01.09.2026)
7. newseria-connector + biznesciti-worker
8. TikTok distribution - po walidacji flow _gotowy.mp4
