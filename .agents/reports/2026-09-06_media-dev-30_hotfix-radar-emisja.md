# Raport: Hotfix Radar & Emisja (Zgodnie z Dispatch)
**Data:** 2026-09-06
**Callsign:** media-dev-30
**Status:** Zakończono z sukcesem ✅

## Wykonane kroki:
1. **Autoryzacja (Złota Zasada):** 
   - Usunięto generowanie tokenów w locie przez `docker exec ... jose jwt`.
   - Zastąpiono czytaniem zmiennej środowiskowej `.env` (`os.environ.get('PRESSAI_JWT_USER')`) w `emisja_sheets_sync.py` oraz `radar_sheets_sync.py`.
   - Dodano rzucanie `RuntimeError` przy braku tokenu z komunikatem "Brak tokenu PRESSAI_JWT_USER w .env".
2. **Refaktoryzacja `radar_sheets_sync.py`:**
   - Zmieniono zakładkę na `Propozycje Radar`.
   - Dostosowano mapowanie do 6 kolumn: A: Temat, B: Źródło, C: Tytuł SEO, D: Frazy kluczowe, E: Obrazek główny, F: Status.
   - Pętla generowania słucha tylko na status `Publikuj w PressAI` i aktualizuje na `Opublikowane` w kolumnie F po udanym wdrożeniu.
   - Dostosowano sekcję *Fetch*, by wstawiała tytuł do pierwszej kolumny.
3. **Rozszerzenie `emisja_sheets_sync.py`:**
   - Dodano obsługę kolumny `Obrazki dodatkowe`.
   - Dodano wczytywanie wielu ścieżek (`split(',')`), z zachowaniem funkcji wgrywającej używanej dla obrazka głównego (`step_upload_image`).
   - Zachowano poprawną pracę dla głównego obrazka.
4. **Deploy na VPS:**
   - Zmodyfikowane skrypty zostały wgrane na serwer VPS (Oracle) i nadpisały wersje uruchamiane z Crona (`/home/ubuntu/media-dispatch/agents/emisja-worker/emisja_sheets_sync.py` i `.../radar-worker/radar_sheets_sync.py`).
   - Zmiany zostały zacommitowane i wypchnięte do remote `main` w `media-dispatch`.

## Potencjalne problemy / Uwagi
* Wdrożono nowy sposób autoryzacji - cron/skrypty korzystające z `emisja_sheets_sync.py` i `radar_sheets_sync.py` MUSZĄ mieć dostarczony w środowisku klucz `PRESSAI_JWT_USER` na VPS.
