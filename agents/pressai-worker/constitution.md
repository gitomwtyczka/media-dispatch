# pressai-worker — Konstytucja

> Plik dla agentów AI które wywołują pressai-worker.  
> Ostatnia aktualizacja: 12.09.2026 | media-dev-B

---

## 1. Tożsamość

| Pole | Wartość |
|------|--------|
| **Callsign** | `pressai-worker` |
| **Warstwa** | Production / Distribution (Warstwa 3) |
| **Stack** | Python 3.10+ · requests · SSE streaming · PressAI API · WordPress REST |
| **Środowisko** | Dowolne środowisko Python (VPS / Local) z łącznością do `press.impresjapr.pl` |
| **Skrypty** | `agents/pressai-worker/auto_publisher.py`, `agents/pressai-worker/worker.py` |

---

## 2. Jak wywołać

### Składnia CLI

```bash
# Sprawdzenie łączności z API PressAI i Feed Crawler
python agents/pressai-worker/worker.py --health

# Pobranie statusu ostatniego przetwarzania
python agents/pressai-worker/worker.py --status

# Publikacja kandydata z automatycznej selekcji Feed Crawlera
python agents/pressai-worker/worker.py --auto-pick --portal Kurier365

# Publikacja ze wskazanego adresu URL
python agents/pressai-worker/worker.py --url "https://biznes.wprost.pl/..." --portal Kurier365 --portal-id 1

# Wywołanie z surowym payloadem JSON
python agents/pressai-worker/worker.py --process '{"source_url": "https://...", "target_portal": "Kurier365"}'
```

### Wywołanie programistyczne (Python)

```python
from agents.pressai_worker.worker import health_check, process, get_status

# 1. Health check
status = health_check()
if status["status"] != "ok" and not status["pressai_connected"]:
    raise RuntimeError("PressAI jest niedostępne")

# 2. Przetwarzanie zadania (Opcja A — direct URL)
task_url = {
    "source_url": "https://www.wnp.pl/energia/przyklad,123.html",
    "source_text": "Opcjonalny kontekst lub wyciąg z artykułu",
    "target_portal": "Kurier365",
    "portal_id": 1,
    "model_provider": "anthropic",
    "model_name": "claude-sonnet-4-5",
    "custom_instructions": "Zoptymalizuj pod Google Discover. Język polski."
}
res_url = process(task_url)

# 3. Przetwarzanie zadania (Opcja B — auto-pick z Feed Crawlera)
task_autopick = {
    "auto_pick": True,
    "portal": "Kurier365",
    "portal_id": 1
}
res_autopick = process(task_autopick)
```

---

## 3. Format output

Każde wywołanie metody `process(task)` zwraca ustrukturyzowany słownik:

```json
{
  "status": "ok",
  "article_id": "art_654321",
  "wp_post_id": 78910,
  "wp_edit_url": "https://kurier365.pl/wp-admin/post.php?post=78910&action=edit",
  "source_url": "https://..."
}
```

W przypadku błędu:

```json
{
  "status": "error",
  "error": "PressAI generate błąd HTTP 500: ...",
  "article_id": null,
  "wp_post_id": null,
  "wp_edit_url": null,
  "source_url": "https://..."
}
```

---

## 4. Parametry i konfiguracja

### Zmienne środowiskowe

| Zmienna | Typ | Domyślnie | Opis |
|---------|-----|----------|------|
| `PRESSAI_JWT_TOKEN` | str | *(wymagany)* | Bearer JWT token autoryzacyjny |
| `PRESSAI_URL` | str | `https://press.impresjapr.pl` | Bazowy URL instancji PressAI |
| `PRESSAI_PORTAL_ID` | int | `1` | Domyślny ID portalu WordPress w PressAI |
| `FEED_CRAWLER_URL` | str | `https://crawler.impresjapr.pl` | URL bazowy Feed Crawlera |

### Domyślne mapowanie portali

| Portal | Portal ID w PressAI | Domenowy WP URL |
|--------|---------------------|-----------------|
| Kurier365 | `1` | `https://kurier365.pl` |
| Prawy.pl | *(dynamiczne z bazy)* | `https://prawy.pl` |
| BiznesCiti | *(dynamiczne z bazy)* | `https://biznesciti.com` |

---

## 5. Integracja z pipeline

```
Źródło: Feed Crawler / Direct URL / RSS / Mail
  ↓
AutoPublisher (pressai-worker)
  ├── 1. Selekcja kandydata (filtry PL/EU, scoring słów kluczowych)
  ├── 2. POST /api/editor/generate (SSE stream, model Claude Sonnet)
  ├── 3. Odczyt article_id (lub fallback POST /api/articles/)
  └── 4. POST /api/publisher/publish/{article_id} [status: draft]
        ↓
WordPress Draft (gotowy do weryfikacji przez Redaktora Naczelnego)
```

---

## 6. Znane pułapki operacyjne

### P1 — Publikacja ZAWSZE jako draft
Naruszenie reguły draft-only i opublikowanie materiału ze statusem `publish` lub `future` bez uprzedniej autoryzacji redaktora naczelnego jest błędem krytycznym. Parametr `status: 'draft'` w payloadzie publikacji jest wymuszony kodowo.

### P2 — Autoryzacja i tokeny JWT
Token NIE może być zapisany na sztywno w kodzie źródłowym ani commitowany do repozytorium. `AutoPublisher` pobiera token wyłącznie ze zmiennej `PRESSAI_JWT_TOKEN` (oraz fallbacków `PRESSAI_JWT_USER`, `PRESSAI_JWT`). Przy braku tokena operacje generowania rzucają natychmiastowy wyjątek walidacyjny.

### P3 — Parsowanie strumienia SSE (`/api/editor/generate`)
Odpowiedź z endpointu generowania jest strumieniem `text/event-stream`. Pole `article_id` może pojawić się na początku lub w końcowych liniach streamu. Jeśli endpoint SSE zwróci treść artykułu bez `article_id`, `AutoPublisher` automatycznie wykonuje fallback do `POST /api/articles/` w celu utrwalenia artykułu i pobrania identyfikatora.

### P4 — Timeouty generowania LLM
Generowanie obszernego artykułu (800-1000 słów) z FAQ przez model Claude może zająć od 30 do 120 sekund. Żądanie HTTP do SSE musi posiadać `timeout` ustawiony na minimum 180 sekund, a połączenie musi być utrzymywane w trybie `stream=True`.

### P5 — Filtrowanie kandydatów w feed-crawlerze
W trybie `auto_pick` API może zwrócić artykuły obcojęzyczne lub o niskiej relewancji. Selekcja priorytetyzuje artykuły z flagami `language='pl'`, `country='PL'` oraz z polskimi słowami kluczowymi gospodarczo-społecznymi (`PL_KEYWORDS`).

### P6 — Brak `wp_edit_url` w odpowiedzi publishera
Gdy WordPress API w PressAI zwróci wyłącznie `post_id` bez bezpośredniego `wp_edit_url`, worker automatycznie konstruuje właściwy adres edycji w kokpicie WordPress (`/wp-admin/post.php?post={id}&action=edit`) na podstawie domeny portalu docelowego.

---

## 7. Raport po zakończeniu

Worker raportuje stan wykonania w standardowym formacie:

```
[pressai-worker | 12.09.2026 HH:MM] STATUS

Zadanie: <auto_pick | direct_url>
Portal docelowy: <portal> (ID: <portal_id>)
Wynik:
  - Article ID: <article_id>
  - WP Post ID: <post_id>
  - WP Draft URL: <wp_edit_url>
  - Source URL: <source_url>

Status: OK / ERROR [opis błędu]
```

---

## 8. Architektura modułu

```python
# Lokalizacja: agents/pressai-worker/
# auto_publisher.py — klasa AutoPublisher (obsługa PressAI HTTP/SSE, selekcja, publikacja)
# worker.py         — publiczny interfejs modułowy (health_check, process, get_status, CLI)
# README.md         — dokumentacja techniczna i instrukcja wdrożeniowa
# constitution.md   — niniejsza konstytucja operacyjna
```

---

*Inicjacja: media-dev-B | 12.09.2026*
