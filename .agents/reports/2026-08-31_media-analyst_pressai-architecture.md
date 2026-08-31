# Raport: Architektura PressAI i Codzienna Produkcja Artykułów Multi-Portal

**Autor:** `[media-analyst | media-dispatch 31.08.2026]`  
**Do:** Redaktor Naczelny / Supervisor 01  
**Temat:** Architektura PressAI, integracja z WordPress oraz uruchomienie codziennej produkcji dla portali (`prawy.pl`, `kurier365.pl`, `biznesciti.com`)

---

## 1. Architektura PressAI

System PressAI składa się z dwóch powiązanych warstw technologicznych:
1. **PressAI SaaS Backend (`crimson-void`)**: FastAPI (Python) działające na VPS (`https://press.impresjapr.pl/api`). Zawiera silnik AI (`AIEngine`), bazę danych SQLite (`saas.db`), moduł integracji WordPress REST API (`WPClient`), moduł Gmail API, moduł ekstrakcji danych ze stron i YouTube (`DataExtractor`) oraz profile stylistyczne portali.
2. **PressAI WordPress Plugin (`pressai-wp`)**: Wtyczka do WordPressa (PHP + Gutenberg Sidebar JS), która umożliwia generowanie i import treści bezpośrednio z poziomu edytora blokowego w WP Admin przy użyciu JWT Bearer auth.

### Flow przetwarzania (Input → Generowanie → Publikacja)

```
[INPUT SOURCES]
 ├── URL (Website scrape / YouTube transcript) -> /api/editor/extract
 ├── Pliki (.docx, .pdf, .odt, .rtf, .html, .vtt, .txt, .md) -> /api/editor/upload
 ├── Gmail (Informacje prasowe, załączniki PDF/DOCX, linki, grafiki) -> /api/gmail/prepare-article
 └── Prompt / Temat redakcyjny (Manual / RSS / Intelligence) -> /api/editor/generate
        │
        ▼
[AI GENERATION ENGINE] (FastAPI: /api/editor/generate lub /api/plugin/generate)
 ├── Dobór Playbooka i profilu portalu (WPPortal.portal_profile / UserPlaybook)
 ├── Wstrzyknięcie whitelistingu linków wewnętrznych (GSC / DB PublishLog)
 ├── Grounding zewnętrzny (Google Trends / Context Intelligence)
 ├── LLM Provider: OpenAI (GPT-4o), Anthropic (Claude Sonnet 4-5)
 ├── Generowanie struktury: H1, lead, H2/H3, FAQ (HTML + JSON-LD), metadane SEO
 ├── AI Compliance & Image placement (<figure>, gallery, ALT/Title/Caption)
 └── Quality Gate (walidacja SEO, długości, formatowania i kompletności)
        │
        ▼
[PUBLICATION ENGINE] (FastAPI: /api/publisher/publish/{article_id} via WPClient)
 ├── WordPress REST API (/wp-json/wp/v2/posts, /media, /tags)
 ├── Upload i przypisanie Featured Image (WebP/JPEG)
 ├── Iniekcja SEO: RankMath (/rankmath/v1/updateMeta) lub Yoast (post_meta)
 ├── Status kontrolny: Domyślnie DRAFT (ochrona przed przypadkową publikacją)
 └── Audit Trail: Zapis do PublishLog (SHA-256 content hash, link WP, post_id)
```

### Konfiguracja portali (Baza danych `WPPortal`)
Portale konfigurowane są w tabeli `wp_portals` modelu SQLAlchemy:
- `id`, `user_id`, `name`: Nazwa portalu (np. `Prawy.pl`, `Kurier365`, `BiznesCiti`).
- `wp_url`: Bazowy URL WordPress (np. `https://prawy.pl`, `https://kurier365.pl`).
- `wp_user` & `wp_app_password`: Autoryzacja przez WordPress Application Passwords (HTTP Basic Auth).
- `default_category_id`: ID domyślnej kategorii w WP.
- `seo_plugin`: `rankmath` lub `yoast` (decyduje o sposobie zapisu focus keyword, meta description, SEO title).
- `default_status`: `draft` (zalecane) lub `publish`.
- `portal_profile`: JSON z profilem generowanym przez AI (`category`, `audience`, `tone`, `topics`, `avoid`, `article_length`, `style_rules`, `seo_notes`).

### Jak dodać nowy portal do systemu?
1. W WordPressie docelowym utworzyć użytkownika redakcyjnego i wygenerować **Application Password** (`Użytkownicy → Profil → Hasła aplikacji`).
2. Wywołać endpoint `POST /api/publisher/portals`:
   ```json
   {
     "name": "Kurier365",
     "wp_url": "https://kurier365.pl",
     "wp_user": "redakcja_ai",
     "wp_app_password": "xxxx xxxx xxxx xxxx",
     "default_category_id": 1,
     "seo_plugin": "rankmath",
     "default_status": "draft"
   }
   ```
3. Uruchomić automatyczne profilowanie portalu: `POST /api/publisher/portals/{portal_id}/analyze` (Claude Sonnet analizuje stronę główną, SERP i artykuły, tworząc profil stylu).
4. Przetestować połączenie: `POST /api/publisher/test/{portal_id}`.

### Główne API Endpoints PressAI
- `POST /api/editor/generate`: Pełne generowanie artykułu ze strumieniowaniem SSE.
- `POST /api/editor/generate-discover`: Generowanie satelity Google Discover + podpięcie do klastra tematycznego.
- `POST /api/editor/generate-video`: Generowanie artykułu wideo pod transkrypcję YouTube.
- `POST /api/publisher/publish/{article_id}`: Publikacja artykułu do WP (draft / new / update).
- `POST /api/plugin/generate`: Synchroniczny endpoint JSON dla wtyczki Gutenberg.
- `POST /api/gmail/prepare-article`: Konwersja maila PR i załączników do źródła artykułu.
- `GET /api/external/seo-data`: M2M endpoint dla zewnętrznych usług (VSE) pobierający frazy GSC i Trends.

---

## 2. Obecna rutyna vs. Pożądana (Codzienna Produkcja)

| Aspekt | Stan obecny (SaaS manualny) | Pożądany stan docelowy (`media-dispatch`) |
|---|---|---|
| **Wybór tematów** | Ręczne wklejanie linków/treści przez człowieka | `feed-crawler` (RSS) + `content-radar` (Trends) + `gmail-worker` |
| **Selekcja i dispatch** | Człowiek decyduje co generować | `redaktor-naczelny` syntetyzuje wywiad i rozsyła taski do workerów |
| **Generowanie** | Kliknięcie w dashboardzie lub Gutenbergu | `pressai-worker` / `vse-worker` wykonują joby autonomicznie |
| **Publikacja do WP** | Ręczne kliknięcie "Publikuj" w panelu | Auto-draft w WP z RankMath SEO, powiadomienie na Discord/Telegram |
| **Harmonogram** | Tabela `tasks` w DB bez automatycznego triggera | Cron/Scheduler orkiestrujący cykle publikacji w ciągu dnia |
| **Czas redakcji** | 20–40 min na artykuł | 1–3 min na zatwierdzenie gotowego draftu w WP |

### Co trzeba dodać, aby uruchomić autonomiczną produkcję?
1. **Task Runner / Dispatcher w `media-dispatch`**: Skrypt/worker (`agents/pressai-worker/`), który odpytuje kolejkę zadań (`shared/tasks/queue.json`), łączy się z API PressAI i publikuje drafty do właściwych portali.
2. **Konektor źródeł (Warstwa 1 Intelligence)**: Połączenie crawlerów RSS i Gmail API z meta-agentem `redaktor-naczelny`.
3. **Konfigurację credentials WP dla wszystkich 3 portali** w bazie SaaS (`WPPortal`).

---

## 3. Propozycja codziennej rutyny — FRAMEWORK dla 3 portali

### Portal 1: `Prawy.pl`
- **Profil:** Publicystyka polityczna, prawo, społeczeństwo, analizy wideo.
- **Częstotliwość:** 6–8 artykułów / dzień.
- **Źródła:** 
  - Wideo i nagrania MP3 z kanałów *Prawy TV* i *Prawy Biblijny* (pipeline VSE Whisper + Short Machine).
  - RSS: portale informacyjne, komunikaty prasowe, maile redakcyjne.
- **Flow:** 
  1. Materiał wideo / RSS → `vse-worker` / `pressai-worker`.
  2. Generowanie artykułu analitycznego (`publication_type: full_analysis`, LLM: Claude).
  3. Upload thumbnail z YouTube jako Featured Media + iniekcja VideoObject Schema & RankMath meta.
  4. Utworzenie wpisu w WP (`status: draft`).
  5. Powiadomienie na Discord/Telegram redaktora.
- **Czas trwania pipeline:** ~4–6 minut (w tym transkrypcja Whisper).
- **Kto zatwierdza:** Redaktor dyżurny Prawy.pl (manualny review draftu i klik "Opublikuj").

### Portal 2: `Kurier365.pl`
- **Profil:** Ogólnoinformacyjny serwis newsowy (kraj, świat, gospodarka, społeczeństwo, technologie).
- **Częstotliwość:** 10–15 artykułów / dzień.
- **Źródła:** 
  - RSS feeds z agencji i portali newsowych (monitoring `feed-crawler` co 30 min).
  - Google Trends PL (szybkie wykrywanie tematów dnia).
- **Flow:** 
  1. `feed-crawler` identyfikuje trending news → `redaktor-naczelny` tworzy task.
  2. `pressai-worker` wywołuje `POST /api/editor/generate` z formatem `news_flash` / `standard` (model: GPT-4o).
  3. Auto-dobór tagów, kategorii i fraz LSI.
  4. Publikacja do WP jako `draft` lub `future` (zaplanowane sloty: 07:30, 09:00, 11:30, 14:00, 16:30, 18:00).
- **Czas trwania pipeline:** ~60–90 sekund / artykuł.
- **Kto zatwierdza:** Półautomatycznie — auto-schedule do WP z 15-minutowym oknem na weto redaktora.

### Portal 3: `BiznesCiti.com`
- **Profil:** Biznes, finanse osobiste, rynek nieruchomości, gospodarka, nowe technologie.
- **Częstotliwość:** 5–8 artykułów / dzień.
- **Źródła:** 
  - Skrzynka Gmail (komunikaty prasowe spółek, raporty rynkowe).
  - Satelity Google Discover powiązane z klastrami tematycznymi (`/api/editor/generate-discover`).
  - RSS serwisów finansowo-gospodarczych.
- **Flow:** 
  1. Nowy mail z raportem/komunikatem → `gmail-worker` (`prepare-article` ekstrahuje załącznik PDF/DOCX i grafikę).
  2. `pressai-worker` generuje artykuł biznesowy z formatem `analiza_rynkowa` / `discover_overlay`.
  3. Dobór linkowania wewnętrznego (GSC pages whitelist).
  4. Publikacja do WP z RankMath SEO i przypisaniem do klastra.
- **Czas trwania pipeline:** ~90–120 sekund / artykuł.
- **Kto zatwierdza:** Redaktor sekcji biznesowej lub auto-draft.

---

## 4. Otwarte pytania do decyzji użytkownika

1. **Credentials WP dla Kurier365 i BiznesCiti:** Czy dla `kurier365.pl` oraz `biznesciti.com` (lub `biznesciti.pl`) zostały już wygenerowane Application Passwords w WordPressie i wprowadzone do bazy `wp_portals` w SaaS?
2. **Klucz API OpenAI / Anthropic na VPS:** Czy produkcyjny backend na VPS ma wystarczające limity tokenów OpenAI (dla `gpt-4o`) oraz Anthropic (dla Claude Sonnet) do ciągłej pracy w pętli batchowej?
3. **Poziom autonomii publikacji:** Czy docelowo dopuszczamy automatyczną publikację (`status: publish` / `future`) dla zaufanych formatów newsowych (np. w Kurier365), czy bezwzględnie każdy artykuł musi przejść przez status `draft` i akceptację człowieka w panelu WP?
4. **Źródła RSS i skrzynki mailowe:** Jakie konkretne adresy RSS (feedy agencji/branżowe) oraz które konta Gmail mają zostać podpięte jako stałe źródła w Warstwie 1 Intelligence?

---

[media-analyst | media-dispatch 31.08.2026] — raport kompletny
