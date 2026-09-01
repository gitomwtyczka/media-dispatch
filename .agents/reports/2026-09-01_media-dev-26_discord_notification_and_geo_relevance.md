# Raport: Discord Notification + GeoRelevanceSignal (kurier365-worker)

**Callsign:** media-dev-26  
**Data:** 01.09.2026  
**Status:** Zakończone sukcesem (Done)

---

## 1. Zrealizowane zadania

### 1.1. GeoRelevanceSignal (`agents/base/trend_signals/geo_relevance_signal.py`)
- Nowy plugin sygnału trendów ważący kandydatów pod kątem polskiego/europejskiego czytelnika.
- Skala mnożnika priorytetu: 0.0 - 2.0.
- Kategorie: `PL-high` (>=1.5), `EU` (>=1.0), `global` (>=0.7), `low` (<0.7).
- **Architektura wg wytycznych media-strateg:**
  - Global/US biznes/polityka/tech (`trump`, `biden`, `wall street`, `fed`, `silicon valley`, `nasdaq`, `ai`, `startup`, `trade war`) mają status ważnych inspiracji globalnych.
  - Niski priorytet (`low`) zarezerwowany wyłącznie dla amerykańskiego entertainmentu (`nfl`, `super bowl`, `kardashian`, `oscars`, `taylor swift concert`) i hiperlokalnych spraw (`city council`, `traffic accident`).
- **Commit SHA:** `8834815e7e38536e8b48c051e557f260fc46c829`

### 1.2. Discord Notification w WorkerBase (`agents/base/worker_base.py`)
- Dodano metodę `notify_discord(candidate, webhook_url=None) -> bool`.
- Rich Embed z kolorystyką zależną od priorytetu:
  - Czerwony (`0xdc3545`) dla P0 (priority >= 8)
  - Pomarańczowy (`0xfd7e14`) dla P1 (priority >= 6)
  - Żółty (`0xffc107`) dla P2 (priority >= 4)
  - Niebieski (`0x1a73e8`) standard
- Flagi i emoji geo (🇵🇱, 🇪🇺, 🌐, ⬇️), źródło, portal, lead oraz trend score.
- **Commit SHA:** `e858bebc14139a6e6aa946b29b798645e3009952`

### 1.3. Integracja w `kurier365-worker/worker.py`
- Zarejestrowano `GeoRelevanceSignal` w `Kurier365Worker.__init__`.
- Dodano powiadomienia Discord dla top kandydatów (`priority >= 6`) po wywołaniu `worker.run()`.
- Dodano funkcję `write_candidates_to_sheets()` oraz metodę `worker.write_to_sheets()` zapisującą kandydatów do arkusza Google Sheets `1HMuODAIOG8e_9VH-HitdL_TwBRwgFZ0vnSKAW7Wmyig` (zakładka `Kandydaci`).
- Dodano flagę CLI `--sheets` oraz weryfikację stanu środowiska w `--health`.
- **Commit SHA:** `00e802cf45995ef10b299568f19ebe147ba01d6b`

---

## 2. Testy GeoRelevanceSignal

| Testowany przypadek | Słowa kluczowe | Wynik Score | Kategoria |
|---------------------|----------------|-------------|-----------|
| **PL (Polityka / Finanse):** *"NBP ogłasza decyzję RPP ws. stóp procentowych. Inflacja i budżet pod kontrolą GUS"* | nbp, rpp, stopy procentowe, inflacja, budżet, gus | **1.80** | `PL-high` |
| **EU (Regulacje / Gospodarka):** *"Komisja Europejska i EBC wprowadzają nowe wymogi AI Act oraz ESG w Brukseli"* | komisja europejska, ebc, ai act, esg, bruksela | **1.30** | `EU` |
| **Global / US Tech & Biznes:** *"Wall Street: Tech layoffs surge as Federal Reserve rate decisions loom and Trump comments on tariffs"* | wall street, tech layoffs, federal reserve, trump, taryfy | **1.10** | `EU / global` |
| **Low Relevance (US Entertainment):** *"NFL Super Bowl party highlights and Taylor Swift concert appearances with Oscars gossip"* | nfl, super bowl, taylor swift concert, oscars | **0.30** | `low` |

---

## 3. Instrukcja dla Użytkownika (Aktywacja Discord & Sheets)

Aby aktywować wysyłkę na kanał Discord oraz zapis do Google Sheets:
1. **Discord Webhook:**
   - Wklej właściwy URL webhooka w pliku `/home/ubuntu/media-dispatch/.env` na VPS:
     ```bash
     DISCORD_WEBHOOK_KURIER365="https://discord.com/api/webhooks/..."
     ```
2. **Google Sheets:**
   - Upewnij się, że plik Service Account znajduje się pod ścieżką zdefiniowaną w zmiennej:
     ```bash
     GOOGLE_SA_FILE="/home/ubuntu/otwock-data/muzeum/muzeum-drive-sa.json"
     ```
   - Arkusz docelowy: `1HMuODAIOG8e_9VH-HitdL_TwBRwgFZ0vnSKAW7Wmyig` (zakładka `Kandydaci`).

---

## 4. Stan repozytorium na VPS
- Repozytorium na VPS (`/home/ubuntu/media-dispatch`) zaktualizowane (`git pull origin main` -> commit `00e802c`).
