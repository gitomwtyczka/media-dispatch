# Handoff — media-dispatch | 31.08.2026

**Sesja:** media-strateg | 31.08.2026 19:00-22:00  
**Następna sesja:** 01.09.2026  
**Model:** Claude Think (sesja zakończona po przekroczeniu V1 RED)

---

## Stan publikacji (źródło: raporty workerów)

| Film / Materiał | WP ID | WP URL | WP status | YT ID | YT status | Data |
|-----------------|:-----:|--------|:---------:|:-----:|:---------:|:----:|
| **Płużański Mosiński 1** | `125353` | [Link WP](https://prawy.pl/porozumienia-sierpniowe-1980-jan-mosinski-o-narodzinach-solidarnosci/) | `publish` (live) | `s6aGNXdtKpA` | `public` ✅ | 2026-08-31 |
| **Płużański Mosiński 2** | `125367` | [Link WP](https://prawy.pl/testament-solidarnosci-czy-idealy-z-1980-roku-przetrwaly-do-dzis/) | `future` (02.09 10:00) | `zYcq-57Y0ts` | `unlisted` ⚠️ | 2026-08-31 |
| **Płużański Rulewski** | `125372` | [Link WP](https://prawy.pl/?p=125372) | `draft` | `EnclbKLEDAA` | `unlisted` | 2026-08-31 |
| **Śliwka** | `0` (brak) | — | HOLD (w VSE status `done`) | `yQ-Q_YrleLE` | — | 2026-08-31 |
| **Biblia 28.08.2026** | `125317` | [Link WP](https://prawy.pl/?p=125317) | `publish` | `S69T_H-DJy4` | `public` ✅ | 2026-08-28 |
| **Biblia 29.08.2026** | `125322` | [Link WP](https://prawy.pl/?p=125322) | `publish` | `HaY1VnzG_3o` | `public` ✅ | 2026-08-29 |

> ⚠️ **Uwaga do Mosińskiego 2 (`zYcq-57Y0ts`)**: Wpis WP zaplanowany na 02.09. Status YouTube został wycofany dwukrotnie przez usera z `public` na `unlisted`. **BEZWZGLĘDNY ZAKAZ zmiany widoczności na public bez jawnej dyspozycji usera.**

---

## Co zrobiono dziś

Wszystkie działania zostały zrealizowane i udokumentowane w commitach:

1. **Publikacja Płużański Mosiński 1 (`s6aGNXdtKpA`)**:
   - Wygenerowano pełną analizę SEO Claude (`publication_type=full_analysis`), wstrzyknięto wpis WP `#125353` (`publish`) i zaktualizowano wideo na YouTube do `public`.
   - Raport: `2026-08-31_media-dev-02_pluzanski-mosinski-1.md` (Commit: `ec5b0f1` / `6559725`).
2. **Pipeline Mosiński 2 (`zYcq-57Y0ts`) & Weryfikacja Śliwki (`yQ-Q_YrleLE`)**:
   - Wygenerowano artykuł WP `#125367` (status `future` na 02.09.2026 10:00), wideo YT ustawione na `unlisted`.
   - Sprawdzono status Śliwki w bazie VSE: 2 wpisy `done`, `wp_id=0` (status HOLD).
   - Raport: `2026-08-31_media-dev-03_mosinski-2-shorts.md` (Commit: `4787634` / `eb56429`).
3. **Pipeline Płużański Rulewski (`EnclbKLEDAA`)**:
   - Utworzono szkic WP `#125372` (`draft`), zaktualizowano metadane SEO na YouTube (status `unlisted`).
   - Zgłoszono 5 zadań renderowania shortów do VSELocalRunner.
   - Raport: `2026-08-31_media-dev-03_rulewski-pipeline.md` (Commit: `21a05fd` / `96fd15d`).
4. **Rendering Shortów na PC (`C:\VSE\Shorts\`)**:
   - Wygenerowano 10 propozycji przez Claude dla Mosińskiego 1 i Mosińskiego 2.
   - Wyrenderowano 10 surowych klipów (`_raw.mp4` + `.srt` + `submachine.srt`) dla Mosiński 1 i Mosiński 2 przez lokalnego runnera.
5. **Implementacja `prawy-studio-worker` MVP v1.0** (w katalogu `agents/prawy-studio-worker/`):
   - `worker.py` (Commit: `32656ff` / `8eb6305`) — główny worker (330 linii) z automatycznym tokenem JWT przez SSH (`docker exec vse-api python3 jose.jwt.encode`), pollingiem napisów YT (`--check-captions`), retry logic 3x, checkpointami w `batch_progress.json` i CLI (`--single`, `--batch`, `--shorts-only`, `--list`, `--reset`).
   - `README.md` (Commit: `6eebe40` / `afb9b37`), `films_template.json` (Commit: `4e17506`), `config.example.json` (Commit: `95561c0`).
   - Retrospektywa z 7 usprawnieniami: `2026-08-31_retro_studio-prawy-pipeline.md` (Commit: `d15416b`).
   - Raport: `2026-08-31_media-dev-04_prawy-studio-worker.md` (Commit: `e83eac2`).
6. **Architektura Flow Redakcyjnego & Integracja Google Sheets**:
   - Opracowano pełne studium optymalizacji pętli zwrotnej z redakcją i wykorzystania Google Sheets jako Editorial Control Center.
   - Raport: `2026-08-31_media-analyst_flow-redakcyjny.md` (Commit: `69ca8b3`).
7. **Architektura Shorts Pipeline & Specyfikacja `shorts-agent`**:
   - Zaprojektowano 4-agentowy pipeline (Ingestion → Generation/Render → Editorial Quality Gate → Optimization/Distribution).
   - Opracowano specyfikację techniczną: `docs/shorts-pipeline-architecture.md` (Commit: `0ed1a98`), `agents/shorts-agent/README.md` (Commit: `931a8b8`), aktualizacja `ROADMAP.md` Faza 1b i 5b (Commit: `76f896c`).
   - Raport: `2026-08-31_media-analyst_shorts-agent-spec.md` (Commit: `fddd618`).

---

## Otwarte zadania

1. **Shorty na dysku PC (`C:\VSE\Shorts\`):**
   - `Płużanski Mosinski 1_2026-08-31\` — 5 klipów `_raw.mp4` gotowych do obróbki montażowej (`_gotowy.mp4`).
   - `Płużanski Mosinski 2_2026-08-31\` — 5 klipów `_raw.mp4` gotowych do obróbki montażowej (`_gotowy.mp4`).
   - `Płużanski Rulewski_2026-08-31\` — 5 klipów przekazanych do renderowania przez VSELocalRunner.
2. **Implementacja `sheets-sync-worker` (Zatwierdzone do realizacji na 01.09.2026):**
   - Utworzenie klienta Google Sheets (`shared/api_clients/sheets_client.py`).
   - Wzbogacenie pipeline'u o automatyczny zapis SEO meta, tytułów, leadów i bezpośrednich linków do edycji WP Draft.
   - Obsługa synchronizacji zmian tytułu z arkusza do WP i YouTube.
3. **Integracja z modułem Short Machine w VSE:**
   - Weryfikacja kontraktu i podłączenie endpointu `POST /v1/shorts/seo-description` po odpowiedzi zespołu VSE.
4. **Weryfikacja statusu publikacji Mosińskiego 2 i Rulewskiego:**
   - Kontrola czy data i stan wpisu WP #125367 (Mosiński 2) oraz WP #125372 (Rulewski) odpowiadają planowi emisyjnemu redakcji.

---

## Otwarte decyzje usera

1. **Data i godzina publikacji Płużański Rulewski (`EnclbKLEDAA`)**:
   - WP #125372 ma obecnie status `draft`, film na YT jest `unlisted`. Czy ustawić konkretną datę `future` czy opublikować `publish`/`public`?
2. **Potwierdzenie publikacji Mosiński 2 (`zYcq-57Y0ts`)**:
   - Zaplanowany w WP na 02.09 10:00 (`future`). Czy zachować ten termin i kiedy przełączyć YT na `public`?
3. **Zezwolenie na wstrzyknięcie i publikację filmu Śliwka (`yQ-Q_YrleLE`)**:
   - Artykuł wygenerowany w VSE (`done`), obecnie na HOLD (`wp_id=0`). Czy wstrzykiwać do WP?
4. **Feedback do pytań o Short Machine API**:
   - Oczekiwanie na potwierdzenie dostępności endpointów w `vse-api`.

---

## Architektura systemu (stan na dziś)

System `media-dispatch` operuje w oparciu o 4 warstwy:

1. **Warstwa 1 — Intelligence (Monitorowanie & Detekcja)**:
   - `youtube-agent` — polling kanału YouTube (`UCoH2G9By4OX3kcLsc8lHgDw`) i gating gotowości napisów ASR.
   - `feed-crawler-worker` & `content-radar-worker` (planowane).
2. **Warstwa 2 — Editorial (Zarządzanie & Koordynacja)**:
   - **Google Sheets Editorial Control Center** (`sheets-sync-worker`) — centralny pulpit redakcji do przeglądu fraz SEO, edycji tytułów/leadów i wglądu w drafty WP.
   - `redaktor-naczelny` (planowany).
3. **Warstwa 3 — Production (Silnik Treści & Wideo)**:
   - `prawy-studio-worker` (`agents/prawy-studio-worker/worker.py` MVP v1.0) — dedykowany orkiestrator pipeline'u VSE (generowanie Claude, inject WP, YouTube metadata, kandydaci shortów).
   - `Short Machine` (moduł VSE) — optymalizacja SEO dla form pionowych 9:16 (`POST /v1/shorts/seo-description`).
   - `VSELocalRunner` — lokalny runner renderujący wycinki wideo na PC z napisami.
4. **Warstwa 4 — Distribution (Dystrybucja Multi-Platformowa)**:
   - `shorts-agent` (`agents/shorts-agent/`) — audyt opublikowanych shortów na YT, wzbogacanie opisów przez Short Machine, generowanie kalendarza `shared/schedules/shorts_schedule.json`.
   - `tiktok-worker` (`agents/tiktok-worker/`) — publikacja zaakceptowanych plików `*_gotowy.mp4`.

---

## Kluczowe pliki i lokalizacje

### GitHub Repositories
- **media-dispatch (`gitomwtyczka/media-dispatch`, branch `main`)**:
  - Worker pipeline: [`agents/prawy-studio-worker/worker.py`](https://github.com/gitomwtyczka/media-dispatch/blob/main/agents/prawy-studio-worker/worker.py)
  - Dokumentacja workera: [`agents/prawy-studio-worker/README.md`](https://github.com/gitomwtyczka/media-dispatch/blob/main/agents/prawy-studio-worker/README.md)
  - Specyfikacja shorts-agent: [`agents/shorts-agent/README.md`](https://github.com/gitomwtyczka/media-dispatch/blob/main/agents/shorts-agent/README.md)
  - Architektura Shorts Pipeline: [`docs/shorts-pipeline-architecture.md`](https://github.com/gitomwtyczka/media-dispatch/blob/main/docs/shorts-pipeline-architecture.md)
  - Mapa drogowa: [`ROADMAP.md`](https://github.com/gitomwtyczka/media-dispatch/blob/main/ROADMAP.md)
  - Heartbeat: [`.agents/heartbeat.json`](https://github.com/gitomwtyczka/media-dispatch/blob/main/.agents/heartbeat.json)
  - Handoff: [`.agents/handoff/2026-08-31_media-strateg_handoff.md`](https://github.com/gitomwtyczka/media-dispatch/blob/main/.agents/handoff/2026-08-31_media-strateg_handoff.md)
- **sonic-void (`gitomwtyczka/sonic-void`, branch `master`)**:
  - Raporty w inbox: `.agents/reports/inbox/2026-08-31_media-*`

### VPS (`ubuntu@147.224.162.100`)
- Ścieżka VSE: `/home/ubuntu/video-seo-engine/`
- Kontenery Docker: `vse-api` (wewnętrzny port **8085**), `vse-web`, `vse-postgres`
- Baza kandydatów: `/home/ubuntu/video-seo-engine/batch/shorts_candidates_2026-08-31.json`

### Lokalne ścieżki PC (Windows)
- Klucz SSH: `C:\Users\tomas2\.ssh\oracle-crimson.key`
- Katalog wideo źródłowych: `C:\Users\tomas2\Videos\Prawy\`
- Katalog wyrenderowanych shortów: `C:\VSE\Shorts\`
  - `C:\VSE\Shorts\Płużanski Mosinski 1_2026-08-31\`
  - `C:\VSE\Shorts\Płużanski Mosinski 2_2026-08-31\`
  - `C:\VSE\Shorts\Płużanski Rulewski_2026-08-31\`

---

## Reguły krytyczne (nie łamać)

1. ⛔ **BEZWZGLĘDNY ZAKAZ PUBLIKOWANIA BEZ JAWNEJ DYSPOZYCJI**:
   - Domyślny status wpisów WordPress to `draft` (lub `future` z wyraźnie ustaloną datą).
   - Domyślna widoczność wideo na YouTube to `unlisted`.
   - Zmiana statusu na `publish` / `public` może nastąpić **WYŁĄCZNIE po jednoznacznej komendzie usera: "opublikuj [nazwa materiału]"**.
   - **Lekcja sesji**: Mosiński 2 został opublikowany 2 razy bez jawnej zgody — zapobiegaj takim sytuacjom.
2. 🛡️ **QUALITY GATE DLA SHORTÓW (Pliki `_raw` vs `_gotowy`)**:
   - Surowe klipy z renderera noszą sufiks `*_raw.mp4`.
   - Żaden agent ani proces automatyczny NIE publikuje plików `*_raw.mp4`.
   - Publikacji (TikTok / YT Shorts) podlegają wyłącznie pliki po weryfikacji i montażu człowieka z sufiksem `*_gotowy.mp4`.
3. 🎯 **DECYZJE STRATEGICZNE DOT. UPLOADU**:
   - Upload shortów na YouTube oraz TikToka realizowany jest ręcznie przez usera/montażystę z poziomu Premiere Pro.
   - Rola `shorts-agent` to audyt jakości, wzbogacanie metadanych SEO przez Short Machine i planowanie harmonogramu publikacji.
4. 🔑 **OPERACJE PLIKOWE I INFRASTRUKTURA VSE**:
   - Pliki repozytorium modyfikowane są **wyłącznie przez GitHub MCP** (zakaz modyfikacji przez `write_to_file` na lokalnym klonie `playground/`).
   - Token JWT generowany dynamicznie przez `jose.jwt.encode()` wewnątrz `vse-api`.
   - W zapytaniach VSE: `llm_provider="claude"`, `publication_type="full_analysis"`, `portal_id` podawany jako UUID (`2b047d7d-15a1-4d2f-8463-f89c2275bb73`).

---

## Następna sesja — pierwsze kroki

1. **Wdrożenie `sheets-sync-worker` (Google Sheets Editorial Control Center)**:
   - Utwórz moduł `shared/api_clients/sheets_client.py` z obsługą API Google Sheets (`gspread`).
   - Zintegruj zapis metadanych SEO (frazy, wygenerowany tytuł, lead, bezpośredni URL do edycji draftu w WP) bezpośrednio po kroku `inject` w `prawy-studio-worker`.
   - Zaimplementuj mechanizm pętli synchronizacyjnej (aktualizacja tytułu/sluga w WP i na YouTube po edycji w arkuszu).
2. **Weryfikacja renderów Rulewskiego**:
   - Sprawdź zakończenie renderowania 5 klipów w `C:\VSE\Shorts\Płużanski Rulewski_2026-08-31\`.
3. **Decyzje emisyjne z userem**:
   - Przedstaw stan materiałów Mosiński 2 (WP #125367 `future`) oraz Rulewski (WP #125372 `draft`) i zapytaj o dyspozycję publikacyjną.
4. **Podłączenie Short Machine**:
   - Po odebraniu specyfikacji endpointu `POST /v1/shorts/seo-description` podłącz generowanie pakietów SEO dla shortów.

---

*[media-dev-09 | media-dispatch 31.08.2026] — handoff kompletny*
