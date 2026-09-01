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

## BLOKERY do następnej sesji

### KRYTYCZNY: Gmail 500 — bug w crimson-void
- `google_credentials = NULL` w tabeli `email_accounts` (saas_database.db, id=12)
- OAuth callback nie zapisuje tokenu do DB
- WYMAGA: dispatch do crimson-void agenta — naprawa routera /api/gmail/auth/callback
- Do momentu naprawy: GmailSource.fetch() zwraca 0 kandydatów

### Prawy.pl portal profile
- W PressAI portal prawy.pl ma błędny profil (AI uznał za portal prawniczy z nazwy domeny)
- Wymaga: POST /api/publisher/portals/3/generate-profile lub ręczna korekta

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
