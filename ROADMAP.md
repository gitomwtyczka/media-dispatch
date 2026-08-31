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

### FAZA 1b: shorts-agent + Short Machine Integration (API gotowe na produkcji od 31.08.2026. Implementacja workers: Q1 09.2026)
- Skanowanie opublikowanych shortów na kanale YouTube Studio Prawy_PL (`UCoH2G9By4OX3kcLsc8lHgDw`)
- Audyt jakości SEO i automatyczne generowanie brakujących opisów przez **Short Machine** (`POST /v1/shorts/describe`)
- Weryfikacja brakujących opisów SM: `description.length < 50` lub tytuł = nazwa pliku mp4
- Aktualizacja snippetu wideo (zoptymalizowany tytuł max 45 zn bez #Shorts, opis 150-350 zn bez URL, max 5 hashtagów bez #Shorts, przypięty komentarz APV) przez YouTube Data API v3
- Silnik harmonogramowania publikacji (`shared/schedules/shorts_schedule.json`): ~6 shortów/film, rozkład na 2-6 dni, peak slots: `07:00`, `12:00`, `18:00`, `21:00` CEST
- Integracja ze strukturą katalogów `C:\VSE\Shorts\[Film]_[date]\` (`*_raw.mp4` vs `*_gotowy.mp4`)

### FAZA 2: Multi-portal Daily Production (Kurier365.pl, BiznesCiti.com, Prawy.pl)

**✅ MVP v0.1 skeleton gotowy (31.08.2026) — media-dev-architect**

Zaimplementowano rozszerzalną architekturę Plugin-based Workers:

#### agents/base/ — bazowa architektura workerów
- `worker_base.py` — WorkerBase, SourcePlugin, TrendSignal, ContentCandidate
- `sources/gmail_source.py` — GmailSource (whitelist), RSSSource (feeds)
- `sources/newseria_source.py` — NewseriaSource z Eco-Bias Gate
- `trend_signals/content_radar_signal.py` — **LIVE** integracja z radar.impresjapr.pl
- `trend_signals/google_trends_signal.py` — fallback placeholder

#### agents/kurier365-worker/ — pierwsza instancja WorkerBase
- `worker.py` — Kurier365Worker (kurier365.pl)
  - Sources: Gmail (Rudziński, Bińczyk, WEI, Biały Kruk), RSS (UOKiK, PAP, Nauka, ISBNews), Newseria
  - Trend Signals: ContentRadarSignal (LIVE gdy CONTENT_RADAR_JWT), Google/Social (fallback)
  - CLI: --health, --run, --top N, --json

#### Następne kroki w Fazie 2:
- **`gmail-kurier365-worker`** — aktywacja GmailSource (token PressAI + PressAI Gmail API)
- **`feed-crawler-worker`** — implementacja RSSSource (feedparser lub feed-crawler serwis)
- **`newseria-connector`** — implementacja scraping sesyjny Newseria
- **`redaktor-naczelny-bot` (Telegram)** — implementacja process() z inline buttons
- **`biznesciti-worker`** — nowa instancja WorkerBase dla biznesciti.com
- **`pressai-worker`** — rozszerzenie o playbooki per portal

### FAZA 3: Content Radar Worker
- **GOTOWE na produkcji (31.08.2026)** — radar.impresjapr.pl
- Google Trends API (pytrends, geo=PL, 7d)
- Social media trending (Twitter/X, TikTok, Instagram, YouTube, Reddit, FB, LinkedIn)
- APScheduler co 15 min
- Viral Score: `views*0.1 + likes*1.0 + shares*3.0 + comments*2.0 + GT_boost`
- Integracja: `ContentRadarSignal` w `agents/base/trend_signals/`
- Endpoint: `GET /api/v1/trending/global` (wymaga JWT + plan Pro)

### FAZA 4: Redaktor Naczelny (Zaawansowana Meta-Orkiestracja)
- Syntetyzuje dane z Intelligence
- Proponuje tematy per portal
- Po GO usera -> dispatch do producentow
- Raport tygodniowy: editorial/YYYY-WW_propozycje.md

### FAZA 5: Multi-platform Distribution
- YouTube worker: upload + scheduling
- TikTok worker: shorty z VSE
- Telegram worker: bot API

### FAZA 5b: TikTok Upload (Gotowe Shorty _gotowy.mp4)
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
1. VSE worker / prawy-studio-worker - zaimplementowany
2. shorts-agent + Short Machine - API gotowe na produkcji od 31.08.2026 (`/v1/shorts/describe`), implementacja workers: Q1 09.2026
3. pressAI worker - kluczowy dla skali
4. **kurier365-worker skeleton v0.1** - architektura gotowa (31.08.2026), aktywacja źrodet: Faza 2
5. Content Radar (radar.impresjapr.pl) - LIVE na produkcji (31.08.2026)
6. redaktor-naczelny-bot (Telegram) - orkiestracja i Human-in-the-Loop
7. newseria-connector + biznesciti-worker
8. TikTok distribution - po walidacji flow _gotowy.mp4
