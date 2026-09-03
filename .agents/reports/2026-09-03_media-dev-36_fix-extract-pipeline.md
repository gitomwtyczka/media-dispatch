# Raport: Zmiana mechanizmu parsowania o 180 stopni dla agentów 

**Data:** 2026-09-03
**Callsign:** media-dev-36

## Cel
Rozwiązanie problemu powstawania suchych artykułów ("golców") poprzez identyfikację różnic między skryptami agentów a panelem UI PressAI (SaaS). 

## Analiza
Po sprawdzeniu zachowania SaaS PressAI we frontendzie oraz na backendzie, ustalono:
1. Panel UI **nie** posiada magicznego endpointu scrapującego obrazki od razu. Używa po prostu `/api/editor/extract`, które zasysa surowy (ale w pełni kompletny) tekst z docelowego artykułu za pomocą CSS selectors / JSON-LD (np. z Onetu).
2. Następnie frontend wysyła pobrany w ten sposób **kompletny tekst** (jako `source_text`) do endpointu `/api/editor/generate`.
3. Agent (w pliku `worker.py` w `media-dispatch`) polegał wyłącznie na zmiennej `candidate.raw_content` lub `candidate.summary` z Feed Crawlera, która nierzadko jest tylko krótkim leadem wyciętym z RSS. Skutkowało to suchymi artykułami, gdyż AI nie miało dostępu do dosłownych wypowiedzi by wygenerować bloki `<blockquote>`.

## Wdrożona zmiana ("o 180 stopni")
1. Dodano nową metodę pomocniczą `_extract_source_text(self, candidate)`, która dla kandydata zawierającego `content_url` **wywołuje scraper API PressAI (`POST /api/editor/extract`)**, pobierając rzeczywistą, natywną zawartość artykułu.
2. Zaktualizowano payload w generowaniu artykułu w taki sposób, aby `source_text` nadpisywany był przez ten natywnie wyekstrahowany, długi artykuł (który zawiera surowe wypowiedzi i pełen kontekst). 
3. Sztuczna inteligencja (`ai_engine.py`), nałożona na bogatszy tekst, samoistnie zacznie produkować formatowane w HTML wstawki `<blockquote>`.

## Potwierdzenie
Operacja została wykonana pomyślnie. Nowe zachowanie naśladuje zachowanie interfejsu SaaS. Kod wdrożono bezpośrednio do pliku `agents/kurier365-worker/worker.py` w repozytorium `media-dispatch`. 

Z poważaniem,
media-dev-36
