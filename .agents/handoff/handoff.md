# Handoff (03.09.2026)
**Agent:** media-strateg (Supervisor)

## Stan prac
1. **Generacja artykułów (PressAI):** Przeprowadziliśmy 3 tury generacji (Kurier365 - ogólne, BiznesCiti - rynkowe, Prawy.pl - konserwatywne). Wykorzystano dedykowane skrypty na VPS uderzające do `/api/editor/generate` (gpt-4o, formaty, faq, is_in_extenso=False). Przetransferowano je do `user_id = 1`.
2. **Problem ("golce"):** Użytkownik zauważył, że artykuły generowane z naszego payloadu są "golcami" (tylko suchy tekst), podczas gdy ręczne wklejenie linku w interfejsie PressAI generuje pełnoprawne artykuły z cytatami, ramkami (`<figure>`), itp. Nasz skrypt przepisywał czysty `content` z Feed Crawlera, pomijając natywne, bardziej zaawansowane mechanizmy web-scrapingu / wzbogacania treści obecne w PressAI.

## Następne kroki (Dla nowego agenta)
- Zrozumieć proces parsowania linków przez backend PressAI: zbadać, jak PressAI obrabia `source_url` (np. czy używa osobnego scrapera, który buduje cytaty i figure'y przed wysłaniem do modelu w `ai_generation.py`). Szukaj też endpointów typu scrape/parse.
- Poprawić nasz mechanizm agentowy, aby triggerował dokładnie tę samą, "bogatą" logikę, którą aktywuje panel PressAI.
- Zmodyfikować payloady skryptów generujących (lub uderzać bezpośrednio pod inny endpoint w PressAI), by artykuły przestały być nagimi tekstami.

## Context Pointers
- Bazy danych: `crawler-db` (feed_crawler), `cr-postgres` (content_radar), `crimson-backend` (saas_database.db SQLite).
- W obecnym kontekście (przed handoffem) stworzono skrypty: `auto_prawy.py`, `auto_biznes.py` używające bezpośrednich postów do `/api/editor/generate`. Mimo wstrzyknięcia odpowiednich ID formatów, teksty są "gołe" w tagi HTML (cytaty, ramki) charakterystyczne dla natywnego scraping'u PressAI.