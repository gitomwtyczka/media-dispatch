# Raport: Grand Unified Architecture (Emisja & Radar)
## Wykonane zadania:
1. **Zbudowano emisja-worker/emisja_sheets_sync.py**
   - Nasluchuje zakladki Emisja.
   - Ignoruje statusy "Opublikowany" / "Zaplanowany".
   - Wgrywa ewentualny lokalny obrazek bezposrednio do bazy WP przez vse-api SSH i przypina do posta.
   - Posiada bezglosny tryb jak biblia-worker.

2. **Zbudowano radar-worker/radar_sheets_sync.py (Nowy Content Radar)**
   - Posiada TRYB FETCH: pobiera tematy z radar.impresjapr.pl i wrzuca do arkusza Google Content Radar ze statusem "Nowa Propozycja".
   - Posiada TRYB PUBLISH: nasluchuje na status "Publikuj w PressAI". Gdy go znajdzie, pobiera Frazy kluczowe, Tytul SEO oraz obrazek, i zrzuca wsad do silnika AI PressAI (/api/editor/generate).
   - Nastepnie zapisuje Draft w historii PressAI i publikuje jako Draft w WordPressie, oraz ustawia obrazek glowny po SSH.

## Problemy i Blokery zdiagnozowane podczas testowania architekury:
- Endpointy PressAI (np. /api/editor/generate) zwracaja 401 (Nie mozna zweryfikowac uprawnien logowania (Niewazny token)) na domyslnym tokenie JWT z backendu PressAI/VSE. Wymaga on podania dedykowanego tokena per-user np. w zmiennej srodowiskowej (podobnie jak robi to kurier365-worker). Nalezy to skonfigurowac w systemie, aby wywolanie PressAI sie powiodlo. Sama architektura skryptu jest gotowa.

Architektura zostala osadzona, a oba skrypty wrzucone do repozytorium.