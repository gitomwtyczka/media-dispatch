# Analiza Integracji: Content Radar × PressAI

## 1. Content Radar API
Content Radar dostarcza informacji o najpopularniejszych trendach na podstawie agregacji z wielu platform (Google Trends, Twitter/X, TikTok, Reddit itp.).
- **Endpointy**:
  - `GET /v1/trending/global` (wymaga planu Pro/Enterprise, zwraca posortowane wg `viral_score`)
  - `GET /v1/posts/` (pełny przegląd z paginacją i filtrami)
  - `GET /v1/posts/public` (podgląd dla tenantów przez X-API-Key)
- **Zwracane dane**: `id`, `title`, `url`, `viral_score`, `share_count`, `source_platform`, `category`, `published_at`, `tenant_id`, `summary`.
- **Agregacja tematyczna**: Zamiast typowych endpointów topicowych, API zwraca konkretne viralowe posty z przeliczonym `viral_score`.

## 2. PressAI: Klastry i Planowanie
W PressAI, tworzenie treści bazuje na Klastrach tematycznych (hub + satelity).
- **Endpointy klastrów (`/api/clusters/`)**:
  - Tryb A (`POST /`): z pojedynczego tematu
  - Tryb B (`POST /from-article/{id}`): z istniejącego artykułu
  - Tryb C (`POST /from-keywords`): z zestawu fraz kluczowych
  - Tryb F (`POST /from-file`): z pliku/transkrypcji
- **Plan Pracy (Tasks)**: Satelity po zatwierdzeniu (`POST /{id}/approve`) tworzą wpisy w tabeli `Task` (z harmonogramem i typem `satellite`).
- **Tworzenie klastra**: Przyjmowane są takie dane jak `name`, `hub_keyword`, `portal`, a satelity są generowane przez AI i uzyskują metrykę `discover_potential` (high/medium/low).
- **Zewnętrzne metryki**: Obecnie klaster nie przechowuje bezpośrednio `viral_score`, ale można zmapować to na pole `discover_potential` satelitów lub wykorzystać w `seo_notes`.

## 3. Odpowiedzi na pytania

### 1. Jak Content Radar może informować PressAI o priorytetach?
Content Radar określa globalne trendy (`viral_score`). Można to wykorzystać na poziomie Warstwy 1 (Media Dispatch), w której agenci pobierają topowe tematy z Radaru, a następnie zlecają PressAI utworzenie klastrów wokół najbardziej viralowych tematów. Dodatkowo, `ContentRadarSignal` w `media-dispatch` może oceniać tematy z RSS (feed-crawler) – jeśli pokrywają się z gorącymi trendami (duży `viral_score`), otrzymują wyższy priorytet (`trend_score`).

### 2. Czy viral_score z Radaru może wchodzić do `selected_phrase` w PressAI?
Tak, `viral_score` może wpływać na dobór fraz (np. jako seed do Trybu C `/from-keywords` w PressAI). W PressAI metrykę tę można także przekuć w atrybut `discover_potential` dla satelitów (im wyższy `viral_score` z Radaru, tym wyższy `discover_potential` satelity), co ułatwi późniejsze sortowanie w Planie Pracy.

### 3. Jak zintegrować bez duplikowania (Content Radar ≠ feed-crawler)?
- **Content Radar** (Warstwa 1) = wyszukiwanie globalnych trendów i sygnałów społecznościowych.
- **Feed-crawler** (Warstwa 1) = stały nasłuch konkretnych źródeł RSS.
- **Integracja**: `media-dispatch` używa `ContentRadarSignal` aby wzbogacić kandydata z RSS. Feed-crawler znajduje artykuł, `ContentRadarSignal` sprawdza czy tytuł/summary pokrywa się z viralowymi trendami z Radaru i podbija priorytet (bag-of-words na tytułach i summary). Tylko tematy z wysokim, zintegrowanym `trend_score` trafiają do PressAI.

### 4. Proponowany flow: Content Radar → ??? → PressAI

**Scenariusz A: Temat generowany z trendów (Trend-driven)**
1. **Content Radar** agreguje trendy i wylicza `viral_score`.
2. **`content-radar-worker` (Media Dispatch)** regularnie pyta `GET /v1/trending/global`, wybiera tematy z `viral_score` > X.
3. Media Dispatch wywołuje **PressAI `POST /api/clusters/from-keywords` (Tryb C)** podając topowe frazy z Radaru.
4. AI w PressAI generuje satelity i oznacza je jako `discover_potential: high`.
5. Automatyczny `approve` przekształca je w zadania w **Planie Pracy (PressAI Tasks)**.

**Scenariusz B: Wzbogacanie newsów (RSS-driven)**
1. **`feed-crawler-worker`** pobiera nowe posty z RSS.
2. Agenci analizują posty za pomocą **`ContentRadarSignal`**, który podbija priorytet (`trend_score`) newsom odpowiadającym trendom w Radarze.
3. Artykuły z najwyższym `trend_score` wysyłane są do PressAI via **`POST /api/clusters/from-article/{id}` (Tryb B)**, tworząc wokół nich klastry tematyczne.
