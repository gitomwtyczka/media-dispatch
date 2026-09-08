# media-dispatch — ROADMAP v2.2
*Zaktualizowany: 2026-09-08 18:30 CEST | Supervisor 03*

---

## 1. Pełna wizja systemu

**media-dispatch** to autonomiczny **Content Operating System (Content OS)** — centrala orkiestracji procesów mediowych, która bez konieczności ciągłej, żmudnej pracy redakcyjnej:
1. Zbiera sygnały, artykuły, wideo i trendy z całego świata (13 000+ źródeł RSS, radary trendów, poczta współpracowników).
2. Analizuje, kategoryzuje i punktuje merytorycznie oraz geograficznie napływające tematy.
3. Prezentuje wyselekcjonowane propozycje w przejrzystych widokach **Google Sheets** w modelu **Human-in-the-Loop** (redaktor decyduje jednym kliknięciem dropdowna o publikacji lub odrzuceniu).
4. Automatycznie uruchamia procesy produkcyjne w dedykowanych silnikach:
   - **PressAI** (`press.impresjapr.pl`) dla pełnych, bogatych artykułów publicystycznych i newsowych,
   - **VSE (Video SEO Engine)** (`vse.impresjapr.pl`) dla transkrypcji, generowania metadanych SEO, rozdziałów i opisów YouTube oraz szkiców WordPress.
5. Dystrybuuje gotowe publikacje do odpowiednich portali WordPress (`prawy.pl`, `kurier365.pl`, `biznesciti.com`) w trybie bezpiecznym (`status: draft`), na kanały YouTube (`Prawy TV`, `Prawy Biblijny`), a docelowo także na TikTok i Telegram.

### Portale docelowe w ekosystemie:
- **prawy.pl** (Portal UUID: `2b047d7d-15a1-4d2f-8463-f89c2275bb73`) — publicystyka, polityka krajowa i zagraniczna, Kościół, tożsamość, patriotyzm, produkcja wideo Prawy TV / Prawy Biblijny.
- **kurier365.pl** (Portal UUID: `dc49d944-188a-4e64-8465-f0a5d6a0221a`) — wydarzenia ogólnoinformacyjne, geopolityka, technologia, nauka, społeczeństwo, sprawy międzynarodowe.
- **biznesciti.com** (Portal UUID: `3bf77e55-26ba-4f0b-b7dc-a79d91d2f4b1`) — biznes, finanse, rynki kapitałowe, gospodarka, prawo gospodarcze, nieruchomości, inwestycje.

---

## 2. Architektura 4 Warstw

```
[ ŚWIAT: RSS / TRENDS / SOCIAL / GMAIL ]
                   │
                   ▼
┌────────────────────────────────────────────────────────┐
│ WARSTWA 1: INTELLIGENCE (Wywiad)                       │
│ - Feed Crawler (13k+ RSS)                              │
│ - Content Radar (Google Trends / Social)               │
│ - Gmail P0 (Materiały współpracowników)               │
│ - Scoring: GeoRelevanceSignal + ContentRadarSignal     │
└──────────────────────────┬─────────────────────────────┘
                           │ routing tematów
                           ▼
┌────────────────────────────────────────────────────────┐
│ WARSTWA 2: EDITORIAL & HITL (Google Sheets)            │
│ Arkusz: 1zqwvS784EaZh1EJIcXk1DliAau1r4X15ENFJjloDSaM   │
│ - Propozycje Radar (prawy.pl)                          │
│ - Propozycje Kurier365 (kurier365.pl)                  │
│ - Propozycje BiznesCiti (biznesciti.com)               │
│ - Emisja (Plan publikacji wideo VSE)                   │
│ - Biblia / Shorty / Kandydaci YT                       │
│ ➔ Decyzja Redaktora: Status = "Publikuj w PressAI" /   │
│                      "Publikuj VSE" / "Odrzucone"      │
└──────────────────────────┬─────────────────────────────┘
                           │ cykliczny sync (cron)
                           ▼
┌────────────────────────────────────────────────────────┐
│ WARSTWA 3: PRODUCTION (Wytwarzanie Treści)             │
│ - PressAI Engine (Extract → Generate → Save Article)   │
│ - Video SEO Engine / VSE (Whisper → SEO Title/Desc)    │
│ - Standalone Workers (Studio Prawy, Biblia Pipeline)   │
└──────────────────────────┬─────────────────────────────┘
                           │ publikacja szkiców / metadanych
                           ▼
┌────────────────────────────────────────────────────────┐
│ WARSTWA 4: DISTRIBUTION (Publikacja)                   │
│ - WordPress REST API (status: draft)                   │
│ - YouTube Data API v3 (status: unlisted)               │
│ - W planach: TikTok, Telegram, Social Media            │
└────────────────────────────────────────────────────────┘
```

---

## 3. Pełny schemat przepływu danych (Data Flow)

1. **Agregacja & Filtracja (Wywiad):**
   - `kurier365-worker/worker.py` uruchamiany co 6 godzin pobiera feedy z `crawler.impresjapr.pl`, filtruje duplikaty względem bazy lokalnej/stanu `shared/state/` i ocenia potencjał artykułu za pomocą `GeoRelevanceSignal` (priorytet Polska, Europa, Świat) oraz `ContentRadarSignal`.
   - Moduł scoringowy przypisuje temat do odpowiedniego profilu redakcyjnego (`kurier365`, `biznesciti`, `prawy`).
2. **Kolejkowanie propozycji w Google Sheets:**
   - Wyselekcjonowane tematy trafiają automatycznie do dedykowanych zakładek arkusza:
     - `Propozycje Radar` (dla prawy.pl),
     - `Propozycje Kurier365` (dla kurier365.pl),
     - `Propozycje BiznesCiti` (dla biznesciti.com).
   - Nowe wiersze otrzymują domyślny status `Nowa Propozycja`.
3. **Interakcja Redaktora (Human-in-the-Loop):**
   - Redaktor przegląda nagłówki, źródła, sugerowane frazy kluczowe i proponowane tytuły SEO.
   - Aby zlecić produkcję, redaktor zmienia status w kolumnie `Status` na:
     - `Publikuj w PressAI` — dla artykułu tekstowego,
     - `Publikuj VSE` — dla materiału wideo (obsługiwane w `Emisja`, wdrażane w zakładkach Propozycji).
   - W przypadku odrzucenia tematu redaktor wybiera `Odrzucone`.
4. **Automatyczna Produkcja & Publikacja Draftu (Sync Scripts):**
   - Dedykowane skrypty synchronizujące uruchamiają się w cyklu minutowym w cronie (`:00`, `:15`, `:30`, `:45`).
   - Skrypt czyta wiersze ze statusem `Publikuj w PressAI`:
     - **Krok 1 (Extract):** `POST /api/editor/extract` — pobranie pełnej treści artykułu źródłowego ze wskazanego URL.
     - **Krok 2 (Generate):** `POST /api/editor/generate` — streamingowe generowanie unikalnego artykułu na portal docelowy w formacie analizy lub reportażu z uwzględnieniem fraz SEO i FAQ.
     - **Krok 3 (Save):** `POST /api/articles/` — zapis artykułu w bazie PressAI powiązanej z UUID portalu.
     - **Krok 4 (Publish):** `POST /api/publisher/publish` — wysyłka artykułu jako `draft` do WordPressa.
     - **Krok 5 (Update Sheet):** Zmiana wartości w kolumnie `Status` na `Opublikowane`.
5. **Obsługa Wideo (VSE Pipeline):**
   - Dla wpisów wideo skrypt `emisja_sheets_sync.py` weryfikuje linki YouTube z zakładki `Emisja`, uruchamia transkrypcję Whisper na serwerze VSE (`vse.impresjapr.pl`), buduje rozdziały, tagi, opis oraz draft wpisu na blogu i wstawia hiperlink do szkicu WP z powrotem do arkusza.

---

## 4. Katalog Workerów (Workers Directory)

| Worker | Ścieżka pliku | Sposób uruchomienia | Rola i zadanie | Status |
|---|---|---|---|---|
| **kurier365-worker** | `agents/kurier365-worker/worker.py` | `python3 agents/kurier365-worker/worker.py --run --sheets` | Agreguje 13k+ RSS z feed-crawlera, analizuje treść, liczy GeoRelevance i scoring, routuje kandydatów i zapisuje do zakładek Google Sheets. | ✅ LIVE (cron co 6h) |
| **kurier365_sheets_sync** | `agents/kurier365-worker/kurier365_sheets_sync.py` | `python3 agents/kurier365-worker/kurier365_sheets_sync.py` | Monitoruje zakładkę `Propozycje Kurier365`, pobiera zadania `Publikuj w PressAI`, generuje artykuł i tworzy WP Draft na `kurier365.pl`. | ✅ LIVE (cron :15) |
| **biznesciti_sheets_sync** | `agents/biznesciti-worker/biznesciti_sheets_sync.py` | `python3 agents/biznesciti-worker/biznesciti_sheets_sync.py` | Monitoruje zakładkę `Propozycje BiznesCiti`, generuje artykuły przez PressAI dla `biznesciti.com` i publikuje szkic WP. | ✅ LIVE (cron :45) |
| **radar_sheets_sync** | `agents/radar-worker/radar_sheets_sync.py` | `python3 agents/radar-worker/radar_sheets_sync.py` | Monitoruje zakładkę `Propozycje Radar`, generuje artykuły przez PressAI dla portalu `prawy.pl` i oznacza wiersz jako `Opublikowane`. | ✅ LIVE (cron :30) |
| **emisja_sheets_sync** | `agents/emisja-worker/emisja_sheets_sync.py` | `python3 agents/emisja-worker/emisja_sheets_sync.py` | Czyta zakładkę `Emisja`, przesyła wideo z YouTube do VSE, generuje draft WP na `prawy.pl` i aktualizuje kolumnę `WP Draft URL`. | ✅ LIVE (cron :00) |
| **prawy-studio-worker** | `agents/prawy-studio-worker/worker.py` | `python3 agents/prawy-studio-worker/worker.py` | Samodzielny worker do produkcji odcinków wideo Studio Prawy_PL z wbudowanym systemem wznawiania i checkpointingu. | ✅ MVP v1.0 |
| **prawy-youtube-worker** | `agents/prawy-youtube-worker/worker.py` | `python3 agents/prawy-youtube-worker/worker.py` | Monitoruje kanał YouTube Prawy TV pod kątem nowych nagrań, pobiera metadane i przekazuje do kolejki wideo. | ✅ v1.0 skeleton |
| **biblia-pipeline** | `agents/vse-worker/scripts/biblia_full_pipeline.py` | `python3 agents/vse-worker/scripts/biblia_full_pipeline.py` | Pipeline audio/tekst dla serii Prawy Biblijny (Whisper → transkrypcja → VSE → WP draft + opis playlisty YouTube). | ✅ standalone (do migracji) |
| **process_shorts_describe** | `agents/vse-worker/scripts/process_shorts_describe.py` | `python3 agents/vse-worker/scripts/process_shorts_describe.py` | Generowanie opisów, tagów i propozycji wycięć shortów z gotowych długich nagrań. | ✅ standalone |
| **sheets-formatter** | `agents/sheets-sync-worker/apply_kandydaci_formatting.py` | `python3 agents/sheets-sync-worker/apply_kandydaci_formatting.py` | Pomocnicze formatowanie stylów komórek, kolorów i reguł warunkowych w Google Sheets. | ✅ pomocniczy |
| **redaktor-naczelny** | `agents/redaktor-naczelny/` | `python3 agents/redaktor-naczelny/worker.py` | Całodobowy autonomiczny redaktor naczelny selekcjonujący co godzinę topowe tematy z wywiadu do Sheets. | 🔴 planowane MVP |
| **shorts-agent** | `agents/shorts-agent/` | `python3 agents/shorts-agent/worker.py` | Moduł integracji z silnikiem Shorts Machine w VSE do automatycznej produkcji rolek/shortów. | 🔴 spec gotowa, czeka na kod |

---

## 5. Zadania Crontab na VPS (`ubuntu@147.224.162.100`)

Konfiguracja crontaba na serwerze produkcyjnym (zastosowano standard `. .env` zamiast `source` oraz kierowanie logów bezpośrednio do katalogu projektu):

```bash
# === MEDIA-DISPATCH CRONTAB ===

# 1. Zbieranie kandydatów ze świata (co 6 godzin)
# Uruchamia pełny pipeline feed-crawlera, scoring i zapisuje wyselekcjonowane tematy do Sheets
0 */6 * * * cd /home/ubuntu/media-dispatch && set -a && . .env && set +a && python3 agents/kurier365-worker/worker.py --run --sheets >> /home/ubuntu/media-dispatch/kurier365-worker.log 2>&1

# 2. Synchronizacja wideo Prawy.pl (co godzinę o :00)
# Przetwarza wiersze w zakładce 'Emisja', generuje transkrypcje i drafty WordPress z VSE
0 * * * * cd /home/ubuntu/media-dispatch && set -a && . .env && set +a && /usr/bin/python3 agents/emisja-worker/emisja_sheets_sync.py >> /home/ubuntu/media-dispatch/emisja-worker.log 2>&1

# 3. Synchronizacja Kurier365 (co godzinę o :15)
# Sprawdza zakładkę 'Propozycje Kurier365', generuje artykuły przez PressAI i publikuje draft na kurier365.pl
15 * * * * cd /home/ubuntu/media-dispatch && set -a && . .env && set +a && python3 agents/kurier365-worker/kurier365_sheets_sync.py >> /home/ubuntu/media-dispatch/kurier365-sheets-sync.log 2>&1

# 4. Synchronizacja Radar Prawy.pl (co godzinę o :30)
# Sprawdza zakładkę 'Propozycje Radar', generuje artykuły przez PressAI i publikuje draft na prawy.pl
30 * * * * cd /home/ubuntu/media-dispatch && set -a && . .env && set +a && /usr/bin/python3 agents/radar-worker/radar_sheets_sync.py >> /home/ubuntu/media-dispatch/radar-worker.log 2>&1

# 5. Synchronizacja BiznesCiti (co godzinę o :45)
# Sprawdza zakładkę 'Propozycje BiznesCiti', generuje artykuły przez PressAI i publikuje draft na biznesciti.com
45 * * * * cd /home/ubuntu/media-dispatch && set -a && . .env && set +a && python3 agents/biznesciti-worker/biznesciti_sheets_sync.py >> /home/ubuntu/media-dispatch/biznesciti-sheets-sync.log 2>&1
```

---

## 6. Zakładki Google Sheets (Human-in-the-Loop & Schema)

**Spreadsheet ID:** `1zqwvS784EaZh1EJIcXk1DliAau1r4X15ENFJjloDSaM`  
**Service Account:** `media-dispatch-sheets@antigravity-mcp-keys.iam.gserviceaccount.com`  
**Klucz na VPS:** `/home/ubuntu/media-dispatch/config/service_account.json` (`GOOGLE_SA_FILE`)

### Spis zakładek w arkuszu:

| Lp. | Nazwa zakładki | GID | Portal docelowy | Przeznaczenie | Interakcja Redaktora |
|---|---|---|---|---|---|
| 1 | **Propozycje Radar** | `514074648` | `prawy.pl` | Propozycje artykułów z wywiadu dla portalu Prawy.pl | Zmiana Statusu: `Publikuj w PressAI` / `Odrzucone` |
| 2 | **Propozycje Kurier365** | `1073549292` | `kurier365.pl` | Propozycje artykułów informacyjnych i geopolitycznych | Zmiana Statusu: `Publikuj w PressAI` / `Odrzucone` |
| 3 | **Propozycje BiznesCiti** | `1900951726` | `biznesciti.com` | Propozycje ze świata biznesu, rynków i gospodarki | Zmiana Statusu: `Publikuj w PressAI` / `Odrzucone` |
| 4 | **Emisja** | `809929940` | `prawy.pl` | Główny harmonogram emisji wideo i powiązań YT ↔ VSE ↔ WP | Wprowadzanie dat, statusów, akceptacja draftów |
| 5 | **Biblia** | `893663019` | `prawy.pl` | Planowanie serii Prawy Biblijny (rozdziały, audio, WP) | Kontrola publikacji odcinków serii |
| 6 | **Shorty** | `767494598` | `prawy.pl` | Zarządzanie krótkimi formami wideo (Shorts/Reels) | Przegląd wygenerowanych opisów i tagów |
| 7 | **Kandydaci YT** | `1644472360` | `prawy.pl` | Zbiór filmów z monitoringu kanałów do potencjalnej obróbki | Oznaczanie statusów obróbki wideo |
| 8 | **Nagrania** | `0` | Archiwum | Historyczna baza nagrań archiwalnych | Widok referencyjny |
| 9 | **Content Radar** | `328988894` | Archiwum | Poprzednia wersja propozycji radaru | Widok archiwalny |
| 10 | **Ostatnie niepubliczne** | `1844067239` | `prawy.pl` | Śledzenie wgrywanych niepublicznych filmów na YouTube | Kontrola gotowości materiałów wideo |

### Standard kolumn w zakładkach Propozycji:
Wszystkie trzy zakładki propozycji (`Propozycje Radar`, `Propozycje Kurier365`, `Propozycje BiznesCiti`) współdzielą jednolity schemat 8 kolumn (A–H):
1. **Temat** (`A`) — skrócony zarys tematu lub oryginalny nagłówek.
2. **Źródło** (`B`) — nazwa agencji, medium lub domeny źródłowej (np. PAP, Reuters, DoRzeczy).
3. **Link do źródła** (`C`) — bezwzględny URL artykułu źródłowego (wykorzystywany przez silnik Extract w PressAI).
4. **Data** (`D`) — data i godzina opublikowania materiału źródłowego.
5. **Tytuł SEO** (`E`) — wygenerowany lub zaproponowany chwytliwy tytuł zoptymalizowany pod wyszukiwarki.
6. **Frazy kluczowe** (`F`) — dobrane słowa kluczowe (comma-separated) do pozycjonowania artykułu.
7. **Obrazek główny** (`G`) — URL lub ścieżka do sugerowanej grafiki głównej.
8. **Status** (`H`) — pole kontrolne z listą rozwijaną (Dropdown):
   - `Nowa Propozycja` — domyślny status po zasileniu przez bota,
   - `Publikuj w PressAI` — polecenie dla workera do pobrania i wygenerowania artykułu,
   - `Publikuj VSE` — w planach: skierowanie do obróbki wideo,
   - `Odrzucone` — odrzucenie tematu przez redaktora,
   - `Opublikowane` — status ustawiany automatycznie przez skrypt po utworzeniu draftu w WordPress.

---

## 7. Portale Docelowe & Konfiguracja UUIDs

Identyfikatory portali w bazie danych `vse-postgres` (tabela `wp_portals`) oraz w silniku PressAI:

| Portal | Domena | Portal UUID (PressAI / VSE) | Zmienna środowiskowa (.env) |
|---|---|---|---|
| **Prawy.pl** | `https://prawy.pl` | `2b047d7d-15a1-4d2f-8463-f89c2275bb73` | `PORTAL_ID` / default `prawy` |
| **Kurier365.pl** | `https://kurier365.pl` | `dc49d944-188a-4e64-8465-f0a5d6a0221a` | `KURIER365_PORTAL_ID` |
| **BiznesCiti.com** | `https://biznesciti.com` | `3bf77e55-26ba-4f0b-b7dc-a79d91d2f4b1` | `BIZNESCITI_PORTAL_ID` |

---

## 8. Stan wdrożenia i Priorytety (08.09.2026)

### ✅ Zamknięte w sesji 3 (08.09.2026):
- Naprawiono błędy A+B w `radar_sheets_sync.py` (`portal_id` → `portal`, fallback dla `source_text`) — commit `9b21743`.
- Dodano dedykowany Service Account `media-dispatch-sheets@antigravity-mcp-keys.iam.gserviceaccount.com` z uprawnieniami edytora do arkusza Google Sheets.
- Wdrożono 3 odrębne zakładki propozycji w arkuszu: `Propozycje Radar`, `Propozycje Kurier365` oraz `Propozycje BiznesCiti`.
- Utworzono i przetestowano skrypty synchronizacji: `kurier365_sheets_sync.py` oraz `biznesciti_sheets_sync.py`.
- Wprowadzono zmienne `KURIER365_PORTAL_ID` i `BIZNESCITI_PORTAL_ID` do produkcyjnego `.env`.
- Poprawiono składnię zadań cron na VPS: użycie `. .env` zamiast `source`, przekierowanie logów do `/home/ubuntu/media-dispatch/`.
- Zresetowano pliki stanu i poprawnie wprowadzono 72 kandydatów do `Propozycje Kurier365`.
- Zaktualizowano ROADMAP do wersji v2.1 (commit `66a6ba7`).

### 🟡 W toku / Znane brakujące elementy:
- **Walidacja danych w Sheets:** brak reguły walidacji danych (dropdown menu) w kolumnie `Status` w nowo utworzonych zakładkach `Propozycje Kurier365` i `Propozycje BiznesCiti`.
- **Zasilanie BiznesCiti:** zakładka `Propozycje BiznesCiti` pozostaje pusta z uwagi na konieczność korekty kryteriów kategoryzacji i routingu w `agents/kurier365-worker/worker.py`.
- **Token Content Radar:** brak zmiennej `CONTENT_RADAR_JWT` w produkcyjnym pliku `.env` na VPS, co wstrzymuje pobieranie trendów social media z `radar.impresjapr.pl`.

### 🔵 Kolejka priorytetów (Najbliższe zadania):
1. **Fix routing BiznesCiti:** Poprawienie warunków klasyfikacji biznes/gospodarka w `agents/kurier365-worker/worker.py`, aby kandydaci biznesowi trafiali do zakładki `Propozycje BiznesCiti`.
2. **Detekcja wideo w skryptach sync:** Dodanie obsługi akcji `Publikuj VSE` w skryptach `radar_sheets_sync.py`, `kurier365_sheets_sync.py` i `biznesciti_sheets_sync.py` (na wzór logiki z `emisja_sheets_sync.py`).
3. **Pobranie i konfiguracja CONTENT_RADAR_JWT:** Zalogowanie do panelu `radar.impresjapr.pl`, wygenerowanie/pobranie JWT i dopisanie do `.env` na serwerze Oracle VPS.
4. **Migracja Biblia Worker do repozytorium:** Wydzielenie skryptów z `agents/vse-worker/scripts/biblia_*.py` i utworzenie uporządkowanego modułu `agents/biblia-worker/` w repozytorium `media-dispatch`.
5. **Redaktor Naczelny MVP:** Implementacja autonomicznego procesu `agents/redaktor-naczelny/worker.py`, który co godzinę automatycznie pobiera topowe propozycje z feed-crawlera i Content Radaru, i zasila arkusz Sheets bez czekania na 6-godzinny batch.
6. **Implementacja Shorts-agent:** Napisanie kodu produkcyjnego w `agents/shorts-agent/` na bazie gotowej specyfikacji technicznej i endpointów Shorts Machine API.

---

*[Supervisor 03 | sonic-void 08.09.2026] — ROADMAP v2.2 wyczerpujący stan ekosystemu*
