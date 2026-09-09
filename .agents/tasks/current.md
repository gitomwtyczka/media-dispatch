## ✅ Zamknięte (10.09.2026 Shorts Runda 3)
- Short `XBhI8nXMpeg` (Ossowski): VSE describe + harmonogram 12.09 18:00 CEST na Studio Prawy_PL
- Grupa B (5 shortów publicznych) + `pPMWUlp0hOY`: VSE describe 2025/2026 wygenerowane z polskimi transkryptami VTT
- Wdrożenie `vse-api:/app/apply_shorts_r3_yt.py` i `/tmp/shorts_r3_results.json`
- Raport dual-write do sonic-void inbox i media-dispatch

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
- Aplikacja snippetów i komentarzy dla 6 shortów po resecie quota YouTube Data API (09:00 CEST)
- Dropdown Status w Propozycje Kurier365 i BiznesCiti (brak walidacji)
- Propozycje BiznesCiti — pusta (problem z routingiem)
- CONTENT_RADAR_JWT — brak w .env

## 🔵 Następne (priorytety)
1. Uruchomienie `apply_shorts_r3_yt.py` po 09:00 CEST
2. Fix routing BiznesCiti w kurier365-worker/worker.py
3. Detekcja video: 'Publikuj VSE' w sync scripts (wzór z emisja_sheets_sync.py)
4. CONTENT_RADAR_JWT z panelu radar.impresjapr.pl
5. Biblia worker — commit lokalnych skryptów do repo (agents/biblia-worker/)
6. Redaktor Naczelny MVP — worker.py który co godz. wrzuca do Sheets automatycznie
7. Shorts-agent — implementacja (spec gotowa od 31.08.2026)
