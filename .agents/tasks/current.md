## ✅ Zamknięte (08.09.2026 sesja 3)
- Bug A+B w radar_sheets_sync.py (portal_id→portal, source_text fallback) — commit 9b21743
- SA media-dispatch-sheets@ dodany do arkusza
- Nowe zakładki: Propozycje Kurier365, Propozycje BiznesCiti
- kurier365_sheets_sync.py, biznesciti_sheets_sync.py — nowe skrypty sync PressAI
- Portal UUIDs w .env: KURIER365_PORTAL_ID, BIZNESCITI_PORTAL_ID
- Crontab fix: . .env zamiast source, logi do /home/ubuntu/media-dispatch/
- State files reset → 72 kandydatów w Propozycje Kurier365
- ROADMAP v2.1 — commit 66a6ba7

## 🟡 W toku
- Dropdown Status w Propozycje Kurier365 i BiznesCiti (brak walidacji)
- Propozycje BiznesCiti — pusta (problem z routingiem)
- CONTENT_RADAR_JWT — brak w .env

## 🔵 Następne (priorytety)
1. Fix routing BiznesCiti w kurier365-worker/worker.py
2. Detekcja video: 'Publikuj VSE' w sync scripts (wzór z emisja_sheets_sync.py)
3. CONTENT_RADAR_JWT z panelu radar.impresjapr.pl
4. Biblia worker — commit lokalnych skryptów do repo (agents/biblia-worker/)
5. Redaktor Naczelny MVP — worker.py który co godz. wrzuca do Sheets automatycznie
6. Shorts-agent — implementacja (spec gotowa od 31.08.2026)
