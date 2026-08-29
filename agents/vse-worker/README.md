# vse-worker (Video SEO Engine Worker)

Autonomiczny worker w architekturze `media-dispatch` odpowiadający za przetwarzanie wideo, generowanie metadanych SEO, draftów WordPress i propozycji Shortów z wykorzystaniem API `video-seo-engine`.

## Kontekst i Reżim Pracy

Worker nie wchodzi z interakcję z kodem produkcyjnym VSE bezpośrednio przez GitHub czy Docker (to zadanie `vse-dev`), lecz komunikuje się z instancją VSE API za pomocą operacji REST (oraz w razie potrzeby przez diagnostyczne komendy SSH).

Szczegółowa wiedza operacyjna, zbiór adresów URL, sposobów autoryzacji, i pułapek przy korzystaniu z instancji jest w Konstytucji Workera: [vse-worker-constitution.md](../../.agents/knowledge/vse-worker-constitution.md).

## Wejście (Input)
Parametry podawane na start procesu:
- `youtube_id` (np. identyfikator filmu)
- `local_path` (opcjonalnie - gdy przetwarzamy plik lokalny MP4/MP3)
- `portal_id` (docelowy portal WordPress)

## Wyjście (Output)
- Wygenerowany szkic (draft) artykułu WordPress
- 10 wygenerowanych propozycji z potencjałem na YouTube Shorts
- Stan zadania zawierający m.in. `schema_data` (VTT transkrypt, SEO metadane, FAQ)

## Uruchamianie i integracja
Oryginalnie funkcjonalność znajdowała się w `batch_vse_pipeline.py`. Worker opakowuje te operacje jako moduł zgodny z reżimem `media-dispatch`, eksponując interfejs (`health_check`, `process`, `get_status`).

## Status
- **Faza 0:** MVP zaimplementowany, w trakcie migracji z repozytorium VSE do `media-dispatch`.