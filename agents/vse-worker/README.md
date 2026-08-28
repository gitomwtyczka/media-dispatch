# vse-worker

Worker Video SEO Engine. Przetwarza filmy YouTube przez VSE API.

## Wejscie
- youtube_id
- local_path (opcjonalnie - plik lokalny MP4)
- portal_id

## Wyjscie
- WP draft (prawy.pl lub inny portal)
- 10 kandydatow shortow
- schema_data w state

## Skrypt
batch_vse_pipeline.py w repo gitomwtyczka/video-seo-engine branch main path batch/

## Status: MVP gotowy