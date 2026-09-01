# Analiza Narzędzi Redakcyjnych i Planistycznych PressAI vs media-dispatch

## Architektura i Przepływ Pracy

```ascii
[Zewnętrzne Źródła: RSS, Gmail, Trendy]
               |
               v
[media-dispatch (WorkerBase)] --(Zbieranie i ocena kandydatów)--> [Google Sheets (Kandydaci)]
               |
               +--(Redaktor Naczelny AI)--> [PressAI API]
                                                 |
                                                 +--> [Clusters] -> [Planner/Tasks]
                                                 |
                                                 +--> [Editor/Generator] -> [Publisher (WP Draft)]
```

## Odpowiedzi na kluczowe pytania

### 1. Czy PressAI ma wbudowany system KLASTRÓW treści i czy można go użyć do planowania?
**TAK.** 
Znaleziono w `backend/routers/clusters.py`. System obsługuje cztery tryby tworzenia klastrów z wykorzystaniem AI:
- z frazy kluczowej (Hub & Spoke),
- z istniejącego artykułu,
- z ręcznie podanych słów kluczowych,
- z tekstu pliku (np. transkrypcja z wideokonferencji).
Po wygenerowaniu satelitów można wywołać endpoint `/{cluster_id}/approve`, który automatycznie tworzy zadania (`Task`) w systemie planowania (Plan Pracy).

### 2. Czy PressAI ma KALENDARZ REDAKCYJNY lub scheduler?
**TAK.**
Zaimplementowany w `backend/routers/tasks.py` oraz `backend/models/editorial.py` (model `Task`). 
Każdy Task posiada parametry `scheduled_date` (np. today, this_week, future), `publish_at` (konkretny timestamp publikacji) oraz `portal`. API udostępnia podstawowy interfejs CRUD do zarządzania tymi zadaniami (np. zmiana statusu).

### 3. Czy PressAI ma mechanizm REKOMENDACJI tematów per portal?
**Częściowo.** 
Posiada generowanie struktury klastrów (satelitów do huba) oraz mechanizm Playbooków (`backend/routers/playbooks.py`), gdzie AI wyciąga z portalu jego styl, profil i zasady. NIE posiada natomiast proaktywnego podpowiadania zupełnie nowych gorących tematów z zewnątrz — polega na zewnętrznym wejściu (użytkowniku lub zewnętrznym agencie podającym słowo kluczowe).

### 4. Czy PressAI ma WORKFLOW zatwierdzania (draft -> review -> publish)?
**TAK.**
Przepływ obejmuje:
1. **Cluster Satellite (Suggested)** -> **Task (Approved)**.
2. Generowanie artykułu przez AI (`backend/routers/editor.py`) z zachowaniem Quality Gate (punktacja i notyfikacje o niskiej jakości).
3. **Draft-First Publisher** (`backend/routers/publisher.py`): domyślnie publikacja odbywa się do szkiców (`draft`) w WordPress. Publikacja z pominięciem draftu (publish) wymaga parametru `force=True`. Zawiera też system przeciwdziałający duplikacjom tematów (`_check_duplicate`).

### 5. Co może REDAKTOR NACZELNY jako agent AI robić przez API PressAI zamiast przez nasz własny pipeline?
Zamiast pisać własne narzędzia planowania w `media-dispatch`, Redaktor Naczelny może:
- Grupać wybrane kandydatury w klastry tematyczne w PressAI (`/api/clusters/from-keywords`).
- Zatwierdzać je do kalendarza redakcyjnego PressAI (`/api/clusters/{id}/approve`).
- Tworzyć gotowe materiały SEO delegując to do `editor.py` (`/api/editor/generate`).
- Publikować automatycznie do WordPress korzystając ze standardowego API PressAI (`/api/publisher/publish`), które już obsługuje optymalizację obrazków wpisów i wtyczki SEO (Yoast, RankMath).

### 6. Co MUSIMY zbudować sami (czego PressAI nie ma):
PressAI jest potężnym silnikiem edycyjno-wydawniczym (backend generujący i planujący treści), ale **nie potrafi aktywnie nasłuchiwać**. Dlatego w `media-dispatch` wciąż musimy mieć zbudowane moduły zbierające (widoczne w `ROADMAP.md` oraz `agents/base/`):
- **Feed monitoring (feed-crawler):** Automatyczny monitoring 13k+ źródeł RSS, ponieważ PressAI potrafi jedynie pobrać zawartość z konkretnego URL po wywołaniu.
- **Gmail P0 stream:** Przechwytywanie i filtrowanie z priorytetyzacją wiadomości mailowych w czasie rzeczywistym.
- **GeoRelevanceSignal & ContentRadar:** Nadawanie wag tematom na podstawie lokalizacji, czy też integracja ze śledzeniem zasięgów w social media (Google Trends/Social).
- **Sheets Kandydaci:** Baza pośrednia, gdzie lądują wszystkie wykryte potencjalne sygnały i artykuły do selekcji. PressAI nie ma odpowiednika dla tak wczesnej, "brudnej" fazy (używa dopiero zadań wyselekcjonowanych do Planu Pracy).

## Rekomendacja
**Wniosek:** `media-dispatch` nie powinien duplikować mechanizmów klastrowania, planowania i wysyłania do WP. Zamiast tego powinien skupić się wyłącznie na Warstwie 1 (Intelligence: FeedCrawler, Gmail, ContentRadar), w której zasila bazę Kandydatów, z której docelowo wywołuje API PressAI do produkcji i organizacji.