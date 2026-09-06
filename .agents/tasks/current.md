## ✅ Zamknięte (06.09.2026)
- [media-dev] Zbudowano architekturę i zaimplementowano workerów `emisja_sheets_sync.py` oraz `radar_sheets_sync.py` obsługujących G-Sheets ("Emisja" i "Content Radar").
- Skrypty uwzględniają tryb bezgłośny dla YT, obsługę lokalnych obrazków do WP (przez docker exec) oraz wsparcie dla generatora PressAI.
- Test wywołał błąd 401 z nowym PressAI API z powodu nieważnego domyślnego backend JWT, co zostało zaraportowane w raportach Inbox/Media-Dispatch.

## 🟡 W toku
- Rozwiązanie problemu konfiguracji tokena `PRESSAI_JWT_USER` w środowisku serwerowym / `.env`, aby backend PressAI pozwolił na autoryzację żądań z poziomu skryptu `radar_sheets_sync.py`.

## 🔵 Następne
1. Wdrożenie na VPS i test w działaniu z pełnym tokenem PressAI.
2. YouTube SEO historyczny update (yt-seo-backlog).
3. Fix Gmail 500 w crimson-void (NULL google_credentials).