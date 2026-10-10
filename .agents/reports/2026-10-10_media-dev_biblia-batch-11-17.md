# Raport: Biblia Batch (11.10 - 17.10.2026)
Callsign: media-dev
Data: 2026-10-10

## Wykonane prace
1. Naprawiono bug step_generate (teraz zwraca schema_data zamiast całego JSON, poprawiono testy).
2. Naprawiono generowanie tokena JWT (wykonywane teraz wewnątrz kontenera se-api przez SSH używając jose.jwt.encode).
3. Przepisano wywołania WP-CLI, aby używały skryptu .sh wgrywanego przez scp z Unixowymi znakami nowej linii (\n), co eliminuje problemy z parsowaniem cudzysłowów i uprawnieniami.
4. Zbudowano i uruchomiono pipeline dla wszystkich 7 filmów z poprawnymi datami.

## Status publikacji

| Data publikacji | yt_id | WP id | WP status / data | YT privacy / publishAt | Verify |
|---|---|---|---|---|---|
| 11.10.2026 | In5b5-k-O2Q | 127909 | future (2026-10-11T00:00:00) | private (2026-10-10T22:00:00Z) | OK |
| 12.10.2026 | SdLkNmBS3uk | 127914 | future (2026-10-12T00:00:00) | private (2026-10-11T22:00:00Z) | OK |
| 13.10.2026 | uP6y29-2QAU | 127918 | future (2026-10-13T00:00:00) | private (2026-10-12T22:00:00Z) | OK |
| 14.10.2026 | gctzm-CTd80 | 127925 | future (2026-10-14T00:00:00) | private (2026-10-13T22:00:00Z) | OK |
| 15.10.2026 | M1bVv8k6FPQ | 127930 | future (2026-10-15T00:00:00) | private (2026-10-14T22:00:00Z) | OK |
| 16.10.2026 | _gZsIsYhVzk | 127935 | future (2026-10-16T00:00:00) | private (2026-10-15T22:00:00Z) | OK |
| 17.10.2026 | ScRgfXz4PMk | 127940 | future (2026-10-17T00:00:00) | private (2026-10-16T22:00:00Z) | OK |

## Weryfikacja
Weryfikacja pierwszego wpisu (In5b5-k-O2Q):
Tytuł zoptymalizowany pod SEO, prawidłowo umieszczony embed wideo. Treść dotyczy 22 rozdziału Ewangelii Mateusza (przypowieść o uczcie królewskiej).

## NIE ZROBIONE / RYZYKA
- Nie usunięto sierot po teście z 12.10, ponieważ nie znaleziono żadnych postów ze słowem "2026-10" mających status draft/future (brak wyników). Zostały prawdopodobnie usunięte wcześniej.
- Istnieje ryzyko, że cache WP może czasem przetrzymywać starsze zapytania, jednak komenda wp cache flush została poprawnie wykonana dla każdego wpisu.
