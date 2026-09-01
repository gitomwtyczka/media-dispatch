# Raport: Implementacja FeedCrawlerSource / RSSSource & Cronjob Kurier365

**Autor:** `media-dev-24`  
**Data:** 01.09.2026  
**Status:** ✅ Sukces (zrealizowany PIVOT na FeedCrawlerSource)

---

## 1. Wykonane zadania

1. **RSSSource v1.0 & FeedCrawlerSource v1.1:**
   - Zaimplementowano plugin `RSSSource` (`agents/base/sources/rss_source.py`) — wsparcie dla RSS 2.0 / Atom i feedparser.
   - Po PIVOT od parenta zaimplementowano plugin `FeedCrawlerSource` (`agents/base/sources/feed_crawler_source.py`) odpytujący centralne API `feed-crawler` (13,982 feedów RSS, 5.96M artykułów).
   - Obsłużono przeglądarkowy User-Agent (dla Cloudflare/Nginx), fallback na `http://localhost:8002` oraz deduplikację w `/tmp/feed_crawler_state_{portal}.json`.

2. **Aktualizacja Kurier365 Worker:**
   - Zaktualizowano `agents/kurier365-worker/worker.py` do użycia `FeedCrawlerSource` z filtrami tematycznymi i priorytetyzacją (UOKiK/konsument: 9, PAP/podatki/RPP: 8, nauka/AI: 7, gospodarka/biznes: 6).

3. **Infrastruktura VPS & Klon Repozytorium:**
   - Klon repo: `/home/ubuntu/media-dispatch` (gałąź `main`).
   - Zainstalowano `feedparser` na VPS.
   - Utworzono i nadano uprawnienia do logu `/var/log/kurier365-worker.log`.

4. **Konfiguracja Cronjob:**
   - Dodano wpis crontab uruchamiający zbieranie co 6 godzin:
     `0 */6 * * * cd /home/ubuntu/media-dispatch && python3 agents/kurier365-worker/worker.py --run >> /var/log/kurier365-worker.log 2>&1`

---

## 2. Wyniki testów LIVE na VPS

- **Stan API feed-crawler:** `https://crawler.impresjapr.pl/api/stats` (wewnętrznie port 8002) — `total_feeds: 13982, total_articles: 5960216, articles_24h: 40150`.
- **Wynik pierwszego uruchomienia `Kurier365Worker.run()`:**
  - Pobranych nowych kandydatów: **10**
  - Przykłady kandydatów:
    1. `[ 8] [feed_crawler:WNP.pl ] Wielka podwyżka podatków. Zabiorą więcej niż kiedykolwiek wcześniej`
    2. `[ 7] [feed_crawler:[Scout] Letsdatascience] Oracle raises capex for AI datacenter buildout`
    3. `[ 7] [feed_crawler:[Scout] Letsdatascience] Brad Paisley Joins Zoo Fight Over AI Data Center`
    4. `[ 7] [feed_crawler:WNP.pl ] W Polsce kolejny weekend dla fotowoltaiki pod górkę`
    5. `[ 6] [feed_crawler:WNP.pl ] Chiński gigant chce być największym producentem samochodów na świecie.`
- **Deduplikacja:** Drugie wywołanie poprawnie pominęło już zapisane artykuły (0 duplikatów).

---

## 3. Commit SHA

- `agents/base/sources/rss_source.py` — commit `c551b05034576eb9f63c0f388031362c66bbe213`
- `agents/base/sources/feed_crawler_source.py` — commit `ce11ebbb8d06e28fd67727d4d107d2d373ee8fd8`
- `agents/kurier365-worker/worker.py` — commit `c5d96df470b1febd788ed1cc125b5419e4349100`
- `agents/kurier365-worker/test_rss.py` — commit `d14dd074b431f6c798037f8b56629d8dabe5aa0a`
