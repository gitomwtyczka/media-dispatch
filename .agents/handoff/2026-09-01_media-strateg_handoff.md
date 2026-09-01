# Handoff — media-strateg | 01.09.2026 18:50

## Status sesji
Kontekst wyczerpany (V1:Flash ~44). Handoff standardowy.

## Co zrobione w tej sesji
- PressAI pipeline działa end-to-end: feed-crawler → generate → WP draft (kurier365 #88470)
- GmailSource z prepare-article flow (automatyczne obrazki P0) — commit 289d878
- RadarEnricher v1.0 per-portal (40c commituje)
- Sheets Kandydaci: kolumny Prompt obraz 1/2, kolory P0-P3
- ROADMAP split Ścieżka A (Editorial) / B (Auto-batch)
- Content Radar architektura: Opcja 1 jako filtr
- docs: pressai-editorial-analysis.md, content-radar-pressai-integration.md, publication-flow.md
- PRESSAI_JWT_USER w .env, crontab z .env (co 6h)
- 18 priorytetowych nadawców Gmail: WEI, Rudiński, Juchniewicz, Bolek, Żabka, Art-Media, XBW...
- Portal Kurier365 id=1, BiznesCiti id=2, prawy.pl id=3 w PressAI

## Architektura (stan na 01.09.2026)

### Repozytoria
- `media-dispatch` (main) — nasz projekt
- `crimson-void` (main) — PressAI backend
- `content-radar` (main) — Radar (NIEZBADANE ENDPOINTY — zadanie dla nowej sesji)

### Pliki kluczowe (media-dispatch):
- `agents/base/sources/gmail_source.py` — GmailSource z prepare-article, PRIORITY_SENDERS (18 nadawców)
- `agents/base/sources/feed_crawler_source.py` — FeedCrawlerSource (departments)
- `agents/base/trend_signals/geo_relevance_signal.py` — GeoRelevanceSignal v1.1
- `agents/base/trend_signals/radar_enricher.py` — RadarEnricher v1.0 per-portal (commit 319a26f)
- `agents/base/worker_base.py` — notify_discord() dual-channel
- `agents/kurier365-worker/worker.py` — 3 strumienie + phrase-candidates + RadarEnricher
- `agents/sheets-sync-worker/apply_kandydaci_formatting.py`
- `docs/pressai-editorial-analysis.md`
- `docs/content-radar-pressai-integration.md`
- `docs/publication-flow.md`

### PressAI portale (portal_id):
- Kurier365 = 1 (https://kurier365.pl, wp_user: blastotoprowpku)
- BiznesCiti = 2 (https://biznesciti.com)
- prawy.pl = 3 (UWAGA: błędny profil — AI uzna za portal prawniczy)

### Sheets:
- Nagrania prawy: `1zqwvS784EaZh1EJIcXk1DliAau1r4X15ENFJjloDSaM`
- Kandydaci Kurier365+BiznesCiti: `1HMuODAIOG8e_9VH-HitdL_TwBRwgFZ0vnSKAW7Wmyig` (GID Kandydaci: 1842692147)

### VPS:
- `.env`: `PRESSAI_JWT` (HS256 bez exp), `PRESSAI_JWT_USER` (365 dni, dla Gmail API), `PRESSAI_URL`, `DISCORD_WEBHOOK_KURIER365=PLACEHOLDER`, `CONTENT_RADAR_URL=https://radar.impresjapr.pl`
- Cronjob: `0 */6 * * * cd /home/ubuntu/media-dispatch && set -a && . .env && set +a && python3 agents/kurier365-worker/worker.py --run`

## BLOKERY do następnej sesji

### KRYTYCZNY: Gmail 500 — bug w crimson-void
- `google_credentials = NULL` w tabeli `email_accounts` (saas_database.db, id=12, `tobroz@gmail.com`)
- OAuth callback nie zapisuje tokenu do DB
- Lokalizacja buga: `/app/routers/gmail.py`, funkcja `_get_gmail_service()`, linia ~54
- Fix: OAuth callback musi zapisać credentials do DB. Dispatch do crimson-void agenta z tym opisem.
- Do momentu naprawy: `GmailSource.fetch()` zwraca 0 kandydatów

### Prawy.pl portal profile
- W PressAI portal prawy.pl ma błędny profil (AI uznał za portal prawniczy z nazwy domeny)
- Wymaga: `POST /api/publisher/portals/3/generate-profile` lub ręczna korekta

## Flow publikacji (działający)
1. `POST https://press.impresjapr.pl/api/editor/phrase-candidates` → `selected_phrase`
2. `POST /api/editor/generate` (SSE stream) → `result.generated_article`
3. `POST /api/articles/` → `article_id`
4. `POST /api/publisher/publish/{article_id}` `{portal_id: 1, status: draft}`
→ Zwraca: `post_id`, `edit_link`

Przykład działający: `kurier365.pl` WP post #88470 (górnicy, 1.09.2026)

## Następne kroki
1. Fix Gmail w crimson-void (NULL credentials) — PRIORYTET
2. Test Gmail stream po naprawie
3. Content Radar API discovery (jakie endpointy ma radar.impresjapr.pl)
4. Uruchomienie pełnego runu kurier365-worker z Radar + Geo scoring
5. Prawy.pl portal profile fix

## Klucze techniczne
- PRESSAI_JWT_USER: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0b2Jyb3pAZ21haWwuY29tIiwiZXhwIjoxODE5Nzk3NDMxfQ.KM0y8_Zs_dV9eaPoTDGqzuCdplpIEJR3Y6O17kTMS6E (365 dni)
- Portal IDs: Kurier365=1, BiznesCiti=2, prawy.pl=3
- VPS: ubuntu@147.224.162.100, klucz: C:\Users\tomas2\.ssh\oracle-crimson.key
- Cronjob: 0 */6 * * * cd /home/ubuntu/media-dispatch && set -a && . .env && set +a && python3 agents/kurier365-worker/worker.py --run
