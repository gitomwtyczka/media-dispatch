# Raport z wdrożenia pressai-worker (AutoPublisher)

**Data:** 2026-09-12  
**Autor:** `media-dev-B`  
**Kontekst zadania:** Budowa pełnoprawnego `pressai-worker` (`auto_publisher.py`, `worker.py`, `README.md`, `constitution.md`) z prototypów brain  
**Repozytorium:** `gitomwtyczka/media-dispatch` (branch: `main`)

---

## 1. Podsumowanie realizacji

Zgodnie ze zleceniem dyspozytorskim zaimplementowano i wypchnięto na zdalne repozytorium GitHub produkcyjną wersję workera `pressai-worker`. Moduł integruje pobieranie materiałów źródłowych (zarówno jawne adresy URL / tekst, jak i automatyczny wybór kandydatów z Feed Crawlera), generowanie artykułów prasowych w PressAI z wykorzystaniem strumienia SSE oraz publikację gotowych materiałów w WordPress.

---

## 2. Zrealizowane komponenty

### 1. `agents/pressai-worker/auto_publisher.py` (commit `9612364`)
- **Klasa `AutoPublisher`** z pełnym interfejsem:
  - `health_check() -> dict`: weryfikuje łączność z PressAI (`/api/publisher/portals`) oraz API Feed Crawlera (proxy lub direct).
  - `process(task: dict) -> dict`: koordynuje cały proces od źródła do publikacji w WordPress.
  - `get_status() -> dict`: zwraca telemetryczny stan workera z historią ostatniego uruchomienia.
- **Konfiguracja środowiskowa**:
  - `PRESSAI_URL` (domyślnie: `https://press.impresjapr.pl`)
  - `PRESSAI_JWT_TOKEN` (pobierany z env, brak jakichkolwiek hardcoded tokenów; fallbacki kompatybilnościowe: `PRESSAI_JWT_USER`, `PRESSAI_JWT`)
  - `PRESSAI_PORTAL_ID` (domyślnie: `1` dla Kurier365)
  - `FEED_CRAWLER_URL` (domyślnie: `https://crawler.impresjapr.pl`)
- **Selekcja Feed Crawler (`auto_pick`)**:
  - Filtrowanie i scoring artykułów (`language='pl'`, `country='PL'`, dopasowania słów kluczowych `PL_KEYWORDS`).
- **Obsługa strumienia SSE w PressAI**:
  - `POST /api/editor/generate` z `stream=True` i `timeout=180s`.
  - Parsowanie eventów SSE i ekstrakcja `article_id` oraz wygenerowanej treści.
  - Automatyczny fallback do `POST /api/articles/` jeśli strumień zwróci treść bez ID.
- **Publikacja WordPress**:
  - `POST /api/publisher/publish/{article_id}`.
  - **Bezwzględna reguła bezpieczeństwa**: wymuszony parametr `status: "draft"` (`publish_as_new: True`) — zakaz publikacji live.
  - Ekstrakcja `wp_post_id` i `wp_edit_url` wraz z fallbackiem konstrukcji linku kokpitu WP per portal.
- **Interfejs CLI**: pełna obsługa uruchomienia z wiersza poleceń.

### 2. `agents/pressai-worker/worker.py` (commit `488fde4`)
- Modułowy wrapper udostępniający metody:
  - `health_check() -> dict`
  - `process(task: dict) -> dict`
  - `get_status() -> dict`
- Obsługa CLI:
  - `--health`, `--status`, `--auto-pick`, `--url`, `--text`, `--portal`, `--portal-id`, `--process`, `--json`.

### 3. `agents/pressai-worker/__init__.py` (commit `d3a1b7e`)
- Czysty pakiet Python eksportujący `AutoPublisher`, `health_check`, `process`, `get_status`.

### 4. `agents/pressai-worker/README.md` (commit `8baf6cc`)
- Wyczerpująca dokumentacja techniczna, opis środowiska, tabelaryczne zestawienie zmiennych środowiskowych, instrukcje CLI i Pythona oraz przykłady wejścia/wyjścia JSON.

### 5. `agents/pressai-worker/constitution.md` (commit `8d73de1`)
- Pełna konstytucja operacyjna zgodna ze wzorcem `agents/transcribe-worker/constitution.md`:
  - Tożsamość, wywołanie programistyczne i CLI, schemat outputu, konfiguracja, pipeline, znane pułapki (P1-P6), format raportowania oraz diagram architektury.

---

## 3. Lista commitów na branchu `main`

1. `9612364` — `feat(pressai-worker): implement AutoPublisher [media-dev-B]`
2. `488fde4` — `feat(pressai-worker): implement worker wrapper and CLI [media-dev-B]`
3. `8baf6cc` — `docs(pressai-worker): update README with complete usage, env vars, and task schema [media-dev-B]`
4. `8d73de1` — `docs(pressai-worker): create worker constitution [media-dev-B]`
5. `d3a1b7e` — `feat(pressai-worker): add __init__.py package exports [media-dev-B]`

---

## 4. Status i rekomendacje

- Wszystkie pliki zostały zweryfikowane na GitHub remote pod kątem integralności treści i formatowania znaków nowej linii.
- Kod został zweryfikowany pod kątem składni i importów (`py_compile`).
- Moduł jest w pełni gotowy do integracji w główny pipeline redakcyjny (np. wywoływany przez Redaktora Naczelnego lub orkiestrator).
