# pressai-worker

**Warstwa:** Production / Distribution (Warstwa 3)  
**Callsign:** `pressai-worker`  
**Stack:** Python 3.10+ · requests · SSE streaming · PressAI API · WordPress REST  
**Środowisko:** VPS / Local PC z dostępem sieciowym do `https://press.impresjapr.pl`

---

## Cel modułu

Autonomiczny worker generowania i publikacji artykułów prasowych.
Łączy inteligencję redakcyjną (źródła feed-crawler, maile, bezpośrednie URL) z backendem PressAI oraz publikacją w WordPress.

Główne możliwości:
- **Auto-pick z Feed Crawlera**: automatyczny wybór najbardziej wartościowego kandydata o tematyce polskiej/europejskiej.
- **Generowanie artykułu**: integracja ze strumieniem SSE w PressAI (`POST /api/editor/generate`) z użyciem modeli Claude (domyślnie `claude-sonnet-4-5`).
- **Publikacja w WordPress**: wstrzykiwanie gotowego artykułu jako draft na właściwy portal (`POST /api/publisher/publish/{article_id}`).
- **Bezpieczeństwo**: bezwzględna zasada publikacji wyłącznie w trybie `draft` (`status='draft'`).

---

## Wymagania i zmienne środowiskowe

Konfiguracja odbywa się przez zmienne środowiskowe:

| Zmienna | Typ | Domyślnie | Opis |
|---------|-----|----------|------|
| `PRESSAI_JWT_TOKEN` | str | *(wymagany)* | Bearer JWT token autoryzacji w PressAI |
| `PRESSAI_URL` | str | `https://press.impresjapr.pl` | Bazowy URL instancji PressAI |
| `PRESSAI_PORTAL_ID` | int | `1` | Domyślny ID portalu WP (1 = Kurier365) |
| `FEED_CRAWLER_URL` | str | `https://crawler.impresjapr.pl` | URL API Feed Crawlera |

Kompatybilność wsteczna: `AutoPublisher` akceptuje również `PRESSAI_JWT_USER` lub `PRESSAI_JWT` jeśli `PRESSAI_JWT_TOKEN` nie został ustawiony.

---

## Uruchomienie

### 1. CLI

```bash
# Health check połączenia z PressAI i Feed Crawlerem
python agents/pressai-worker/worker.py --health

# Auto-pick z feed-crawlera i publikacja jako draft
python agents/pressai-worker/worker.py --auto-pick --portal Kurier365

# Przetwarzanie ze wskazanym adresem URL
python agents/pressai-worker/worker.py --url "https://przyklad.pl/artykul" --portal Kurier365

# Przetwarzanie pełnego zadania JSON
python agents/pressai-worker/worker.py --process '{"source_url": "https://...", "target_portal": "Kurier365", "portal_id": 1}'
```

### 2. Wywołanie w Pythonie

```python
from agents.pressai_worker.worker import health_check, process, get_status

# Sprawdzenie dostępności usług
health = health_check()
print(health)

# Wykonanie zadania z direct URL
task = {
    "source_url": "https://www.wnp.pl/energia/przyklad,123.html",
    "source_text": "Opcjonalny fragment lub wstęp...",
    "target_portal": "Kurier365",
    "portal_id": 1,
    "model_provider": "anthropic",
    "model_name": "claude-sonnet-4-5",
    "custom_instructions": "Napisz przystępny artykuł w języku polskim zoptymalizowany pod Google Discover."
}
result = process(task)
print(result)

# Wykonanie zadania w trybie auto-pick
auto_task = {
    "auto_pick": True,
    "portal": "Kurier365",
    "portal_id": 1
}
auto_result = process(auto_task)
print(auto_result)
```

---

## Format danych

### Wejście (`task: dict`)

```json
{
  "source_url": "https://...",
  "source_text": "opcjonalny tekst źródłowy",
  "auto_pick": false,
  "target_portal": "Kurier365",
  "portal_id": 1,
  "model_provider": "anthropic",
  "model_name": "claude-sonnet-4-5",
  "custom_instructions": "..."
}
```

### Wyjście sukcesu (`result: dict`)

```json
{
  "status": "ok",
  "article_id": "art_987654",
  "wp_post_id": 43210,
  "wp_edit_url": "https://kurier365.pl/wp-admin/post.php?post=43210&action=edit",
  "source_url": "https://..."
}
```

### Wyjście błędu (`result: dict`)

```json
{
  "status": "error",
  "error": "Szczegółowy opis błędu",
  "article_id": null,
  "wp_post_id": null,
  "wp_edit_url": null,
  "source_url": "https://..."
}
```

---

## ⛔ Bezwzględne reguły bezpieczeństwa

1. **Status ZAWSZE `draft`**: żaden artykuł nie może zostać opublikowany bezpośrednio na portal (zakaz statusu `publish`).
2. **Brak tokenów w repo**: sekrety wyłącznie przez zmienną środowiskową `PRESSAI_JWT_TOKEN`.
3. **Brak hardcoded treści**: wszelkie adresy URL i teksty przekazywane są dynamicznie w tasku.

---

## Architektura i pliki

- `auto_publisher.py` — klasa główna `AutoPublisher` realizująca komunikację HTTP/SSE, selekcję kandydatów, generowanie i publikację.
- `worker.py` — standardowy modułowy wrapper (`health_check`, `process`, `get_status`) oraz interfejs CLI.
- `constitution.md` — konstytucja workera i wzorzec operacyjny dla agentów AI.
