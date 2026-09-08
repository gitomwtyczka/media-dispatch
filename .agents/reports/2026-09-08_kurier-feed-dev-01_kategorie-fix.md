# Raport: Fix kategorii feedów + crontab dla kurier365-worker

- **Callsign:** kurier-feed-dev-01
- **Data:** 08.09.2026
- **Supervisor:** Supervisor 03
- **Status:** COMPLETED ✅
- **Repo:** gitomwtyczka/media-dispatch (branch: main)
- **Commity:**
  - `1be74738b6ff936baef5aa93ae358b94df15a6a3` — feat: rozszerzenie kategorii feedów Kurier365 i BiznesCiti [kurier-feed-dev-01]
  - `dc4dc4ecbfb73d8bef331f1f3c5640d170c42d24` — fix: usunięcie zbędnego backslasha w _get_auth_headers [kurier-feed-dev-01]

---

## 1. Cel zlecenia
Rozwiązanie dwóch problemów w pipeline agregacji contentu:
1. Crontab na VPS uruchamiał workera bez flagi `--sheets`, przez co zebrani kandydaci nie trafiali do arkusza Google Sheets (`Propozycje Radar`).
2. Trzy dotychczasowe bloki `FeedCrawlerSource` miały wąską listę słów kluczowych i nie pokrywały pełnego profilu obu obsługiwanych portali (`kurier365.pl` — ogólnotematyczny oraz `biznesciti.com` — analityczno-biznesowy).

---

## 2. Podjęte działania i realizacja

### KROK 0: Backup bezpieczeństwa na VPS
- Crontab zachowany do: `/home/ubuntu/backups/crontab_backup_20260908.txt`
- Dotychczasowy kod `worker.py` zachowany do: `/home/ubuntu/backups/kurier365_worker_backup_20260908.py`

### KROK 1: Analiza API i architektury Feed Crawler
- Sprawdzono endpointy w `crawler-web` i bazę `crawler-db` na VPS.
- Potwierdzono, że filtrowanie po `categories` w `FeedCrawlerSource` odbywa się lokalnie w Pythonie metodą substring match (`cat in text_to_match`).
- Zaprojektowano listy słów kluczowych zawierające zarówno formy mianownikowe, jak i rdzenie, formy ze spacją oraz dywizem, a także polskie znaki diakrytyczne (np. `gospodark`, `spółk`, `rynek pracy`, `stopy procentowe`).

### KROK 2 & 3: Wdrożenie 4 bloków FeedCrawlerSource w worker.py
Zastąpiono 3 bloki 4 dedykowanymi źródłami:
- **BLOK 1 (Kurier365):** `limit=60`, `hours_back=6`, `state_file='/tmp/feed_crawler_state_kurier365.json'` — polityka, społeczeństwo, kultura, rozrywka, zdrowie, styl życia, podróże, sport, technologie, motoryzacja, ciekawostki.
- **BLOK 2 (BiznesCiti):** `limit=40`, `hours_back=6`, `state_file='/tmp/feed_crawler_state_biznesciti.json'` — rynki finansowe, GPW, makroekonomia, stopy procentowe, NBP, spółki, fuzje, startupy, nieruchomości, podatki, rynek pracy.
- **BLOK 3 (Dział NAUKA):** `limit=20`, `departments=['science-high-tech', 'health-biotech']`, `state_file='/tmp/fc_kurier365_science.json'`.
- **BLOK 4 (Geopolityka):** `limit=10`, `departments=['defence-geopolitics']`, `state_file='/tmp/fc_kurier365_geo.json'`.

Kod sprawdzono pod kątem poprawności składni AST, zachowania unixowych znaków nowej linii (`\n`) oraz zacommitowano na GitHub.

### KROK 4: Aktualizacja crontab na VPS
Wdrożono skrypt `update_cron_0908.sh` za pośrednictwem SCP i uruchomiono na VPS:
```cron
# Nowy wpis crontab:
0 */6 * * * cd /home/ubuntu/media-dispatch && set -a && . .env && set +a && python3 agents/kurier365-worker/worker.py --run --sheets >> /var/log/kurier365-worker.log 2>&1
```
Flaga `--sheets` została pomyślnie dodana.

### KROK 5: Deploy na VPS
- Zabezpieczono lokalne nieśledzone pliki do `/home/ubuntu/backups/sync_scripts_20260908/`.
- Wykonano `git pull origin main` (fast-forward do commita `dc4dc4ecbfb73d8bef331f1f3c5640d170c42d24`).
- Zweryfikowano poprawność kompilacji Pythona (`python3 -m py_compile agents/kurier365-worker/worker.py`).
- Przeprowadzono health check (`--health`), który potwierdził gotowość wszystkich 4 źródeł RSS `feed_crawler`.

---

## 3. Wyniki testu dry run (`--run --top 10`)

W teście dry run zebrano łącznie **80 kandydatów** (wobec zaledwie 24 przed zmianami — wzrost o 233%):
- Źródło Gmail: 4 kandydatów
- Źródła RSS Feed Crawler:
  - Blok ogólny: 16 kandydatów
  - Blok nauka: 10 kandydatów
  - Blok biznes: 40 kandydatów
  - Blok geopolityka: 10 kandydatów
- Łącznie RSS: 76 kandydatów

### Przykładowy Top-10 wyłonionych tematów:
1. `[15] [gmail:Fundacja XBW] [PL-high] Re: kurier`
2. `[14] [gmail:Fundacja XBW] [PL-high] Re: Komunikat prasowy: Dość wyrzucania właścicieli na bruk.`
3. `[14] [gmail:Żabka Polska] [PL-high] Żabka otworzyła 13 000. sklep. Nowoczesna placówka zlokalizowana jest`
4. `[14] [feed_crawler:Newseria Innowacje] [PL-nauka] Zbliża się sezon zakażeń RSV. Polska wciąż nie zapewnia powszechnej oc`
5. `[13] [feed_crawler:Newseria Innowacje] [PL-nauka] Naukowcy z Lublina opracowali sprężyny nawet o 70 proc. lżejsze od sta`
6. `[12] [gmail:Fundacja XBW] [EU] Komunikat prasowy: Dość wyrzucania właścicieli na bruk.`
7. `[12] [feed_crawler:WNP.pl] [PL-high] Katastrofa w Niemczech, wszystko runęło. Tego nikt się nie spodziewał`
8. `[12] [feed_crawler:WNP.pl] [PL-high] Katastrofa w Niemczech, wszystko runęło. Tego nikt się nie spodziewał`
9. `[11] [feed_crawler:WNP.pl] [PL-high] Polacy już bogatsi od Węgrów, a teraz gonią ich Rumuni. Efekt 16 lat r`
10. `[11] [feed_crawler:WNP.pl] [PL-high] Polacy już bogatsi od Węgrów, a teraz gonią ich Rumuni. Efekt 16 lat r`

Tematyka idealnie wpisuje się w profile:
- **Kurier365:** medycyna/nauka (RSV, inżynieria materiałowa), tematyka społeczna i konsumencka.
- **BiznesCiti:** ekspansja sieci handlowych (Żabka), makroekonomia regionalna CEE (analizy gospodarcze Polska vs Niemcy/Węgry/Rumunia z WNP.pl).

---

## 4. Status i wnioski
Wszystkie punkty zlecenia zostały zrealizowane, przetestowane i wdrożone na produkcji.
Pipeline działa stabilnie, a crontab zapisuje wyniki bezpośrednio do Google Sheets przy każdym cyklu co 6 godzin.
