# Raport: biblia-worker merge

## Zmiany
- pipeline.py: Dodano guard transkryptu (fallback MP4), idempotencję z /v1/check, status embeddable, YT schedule (private/public), kategorię WP 'Biblia', fail-fast (4xx/invalid_grant).
- worker.py: Poprawki dla zoneinfo i parsowania strefy CEST/CET. Dodano tryb batch (z obsługą zatrzymania przy invalid_grant) i dry-run.
- un_batch.py: Naprawiono problem z importami pakietów (dodano modyfikację sys.path).
- iblia_schedule_pipeline.py: Poprawka buga w logowaniu błędu (NameError f-string).
- Utworzono testy (pytest: sprawdzają idempotencję, validację dat, blokadę przy braku transkryptu, fail-fast).

## Wyniki testów
- python -m py_compile: OK
- worker.py --dry-run: OK
- pytest tests/test_biblia_worker.py: 5 passed w 0.13s.

## Ryzyka
- Rzeczywisty kod fallback (wyciąganie MP3 i /v1/audio/generate) nie został w pełni zaimplementowany, ponieważ wymaga ręcznej adaptacji poza zakresem iblia_schedule_pipeline.py. Worker zwróci błąd wymagający interwencji.

[media-dev]
