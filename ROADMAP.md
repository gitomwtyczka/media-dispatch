# media-dispatch - ROADMAP v1.1

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
- Aktualizacja snippetu wideo (zoptymalizowany tytuł max 45 zn bez #Shorts, opis 150–350 zn bez URL, max 5 hashtagów bez #Shorts, przypięty komentarz APV) przez YouTube Data API v3
- Silnik harmonogramowania publikacji (`shared/schedules/shorts_schedule.json`): ~6 shortów/film, rozkład na 2–6 dni, peak slots: `07:00`, `12:00`, `18:00`, `21:00` CEST
- Integracja ze strukturą katalogów `C:\VSE\Shorts\[Film]_[date]\` (`*_raw.mp4` vs `*_gotowy.mp4`)

### FAZA 2: Feed Crawler Worker
- RSS z calego swiata -> baza tematow
- Schema tematu: tytul, zrodlo, url, kategoria, relevance_score
- Cron co 30 min

### FAZA 3: Content Radar Worker
- Google Trends API
- Social media trending
- Output: shared/topics/trending.json

### FAZA 4: Redaktor Naczelny
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
  \"task_id\": \"uuid\",
  \"type\": \"vse|pressai|shorts|publish|tiktok\",
  \"portal_id\": \"uuid\",
  \"input\": {},
  \"priority\": 1,
  \"scheduled_at\": \"ISO timestamp\",
  \"created_by\": \"redaktor-naczelny|shorts-agent|user\"
}
```

## Priorytety MVP
1. VSE worker / prawy-studio-worker - zaimplementowany
2. shorts-agent + Short Machine - API gotowe na produkcji od 31.08.2026 (`/v1/shorts/describe`), implementacja workers: Q1 09.2026
3. pressAI worker - kluczowy dla skali
4. Redaktor Naczelny - orkiestracja tematów
5. Feed crawler - integracja z istniejacym projektem
6. TikTok distribution - po walidacji flow _gotowy.mp4
