# media-dispatch - ROADMAP v1.0

## Wizja

media-dispatch to Content Operating System - system agentow AI
ktory bez recznej pracy zbiera tematy, produkuje tresci i dystrybuuje
je na wiele platform jednoczesnie.

## Architektura 4-warstwowa

[Wywiad] -> [Redaktor Naczelny] -> [Producenci] -> [Platformy]

## Fazy

### FAZA 0: Fundament (teraz)
- Repo + workspace + AGENTS.md
- Migracja batch_vse_pipeline.py jako agents/vse-worker/
- Wspolny API client shared/api_clients/

### FAZA 1: pressAI Worker
- Wejscia: email, URL, tekst
- Wyjscie: artykul na portal WordPress
- Mapowanie API pressAI

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

## Standardy techniczne

### Agent interface
Kazdy worker musi implementowac:
- health_check() -> bool
- process(task: Task) -> Result
- get_status() -> WorkerStatus

### Task schema
{
  task_id: uuid,
  type: vse|pressai|shorts|publish,
  portal_id: uuid,
  input: {},
  priority: 1-5,
  scheduled_at: ISO timestamp,
  created_by: redaktor-naczelny|user
}

## Priorytety MVP
1. VSE worker - juz gotowy, do migracji
2. pressAI worker - kluczowy dla skali
3. Redaktor Naczelny - nawet bez feed-crawlera
4. Feed crawler - integracja z istniejacym projektem