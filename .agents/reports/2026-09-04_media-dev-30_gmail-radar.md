# Raport sesji: media-dev-30 [04.09.2026]
**Temat**: Naprawa logiki filtrowania i heurystyki w GmailSource oraz wstępny test Radaru.

## Zrealizowane zadania:
1. **Filtrowanie twardych maili (GmailSource)**
   Usunięto przestarzałe "display names" i wdrożono bezbłędne filtrowanie po czystych adresach e-mail w oparciu o pełną, podaną przez Redaktora listę, używając:
   - `PRIORITY_DOMAINS` (np. `@art-media.com.pl`, `@wei.org.pl`, `@zabka.pl`, `@uokik.gov.pl`)
   - `PRIORITY_EMAILS` (indywidualne kontakty e-mail dla kluczowych autorów: A. Bińczyk, T. Płużański, C. Rudziński, J. Bolek, M. Gryżewski, B. Kalinowska).
2. **Heurystyka "Materiał" vs "Ping"**
   Odrzucanie maili poniżej 100 znaków jako "ping" LUB bez słów kluczowych "zaproszenie, komunikat..." LUB bez jakichkolwiek załączników. Kod odrzuca teraz krótką wymianę zdań z współpracownikami.
3. **Testowanie Content Radar**
   Workera można bezpiecznie uruchomić w trybie testowym używając:
   `python agents/kurier365-worker/worker.py --source feedcrawler --run`
   Wykonano próbny zrzut logów (brak środowiskowego tokena `CONTENT_RADAR_JWT`, test wyłapał i bezpiecznie pominął radar).

## Pozostało:
- Redaktor przejmuje kontrolę na nowym chacie, by samodzielnie dostarczyć token JWT dla testów lub przetestować workera na serwerze (gdzie jest on zdefiniowany).
