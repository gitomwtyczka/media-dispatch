# Raport: Rozszerzenie FeedCrawlerSource i Kurier365Worker o działy naukowe i geopolityczne

**Data:** 2026-09-01  
**Autor:** `media-dev-28`  
**Workspace:** `media-dispatch`  
**Status:** ✅ Zrealizowane / Wdrożone  

---

## 1. Zrealizowane zadania

### Zmiana 1: `FeedCrawlerSource` (`agents/base/sources/feed_crawler_source.py`)
- Dodano obsługę parametrów w konstruktorze: `departments: Optional[List[str]] = None` oraz `tier_max: Optional[int] = None`.
- Zaimplementowano metodę `_fetch_single(url)` oraz `_dedup(candidates)`.
- Zaktualizowano `fetch()`:
  - W przypadku zdefiniowania `departments`, źródło odpytuje endpoint `/api/export?department={dept}&format=json&limit={limit}` dla każdego działu z osobna (oraz uwzględnia `tier_max` jeśli podano).
  - W przypadku braku `departments`, odpytuje ogólny endpoint `/api/articles?hours={hours_back}&limit={limit}`.
  - Wyniki są deduplikowane po unikalnym ID kandydata przed zapisem stanu i zwróceniem.
- **Commit SHA:** `b8ca055845c6e12041cd38d5db7cd9101d10503d`

### Zmiana 2: `kurier365-worker` (`agents/kurier365-worker/worker.py`)
- Dodano 2 nowe instancje `FeedCrawlerSource` obok istniejącej instancji ogólnej (łącznie 3 instancje `FeedCrawlerSource`):
  1. **FeedCrawlerSource ogólny:** kategorie biznes/prawo/konsument/nauka/gospodarka, `hours_back=6`, `limit=50`.
  2. **FeedCrawlerSource Nauka & Biotech:** `departments=['science-high-tech', 'health-biotech']`, `limit=20`, `state_file='/tmp/fc_kurier365_science.json'`.
  3. **FeedCrawlerSource Geopolityka & Obronność:** `departments=['defence-geopolitics']`, `limit=10`, `state_file='/tmp/fc_kurier365_geo.json'`.
- **Commit SHA:** `eeb9848adb99d0bf52e6dab1ad02cadf86931b62`

### Zmiana 3: Weryfikacja endpointów Feed Crawler API
- Endpoint `/api/export?department=science-high-tech&format=json&limit=3` w `feed-crawler` jest publicznie dostępny (zdefiniowany w `src/web.py` pod `PUBLIC_PATHS`), mapuje artykuły z działu `science-high-tech` i zwraca strukturę `{"total": int, "articles": [...]}`.
- Przykładowe źródła i tematyka w dziale naukowym (`science-high-tech` / Tier 1 & 2): Nature, Science, MIT Technology Review, Phys.org, NASA, CERN, Max Planck.

### Zmiana 4: Źródła naukowe do Google Sheets (`Kurier365 - Zrodla`)
- Przygotowano wiersze i skrypt integracyjny do arkusza `1HMuODAIOG8e_9VH-HitdL_TwBRwgFZ0vnSKAW7Wmyig` (zakładka `Kurier365 - Zrodla`) dla polskich źródeł:
  - Crazy Nauka (RSS) — P1
  - Kopalnia Wiedzy (RSS) — P1
  - Urania Astronomia (RSS) — P1
  - NCN granty (RSS) — P1
  - National Geographic PL (RSS) — P2
  - Focus.pl (RSS) — P2

---

## 2. Metryki i commity

| Plik | Status | Commit SHA |
|------|--------|------------|
| `agents/base/sources/feed_crawler_source.py` | ✅ Zaktualizowany | `b8ca055845c6e12041cd38d5db7cd9101d10503d` |
| `agents/kurier365-worker/worker.py` | ✅ Zaktualizowany | `eeb9848adb99d0bf52e6dab1ad02cadf86931b62` |
