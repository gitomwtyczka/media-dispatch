# Raport: biblia-worker merge V2

## Tabela Zmian

| Wymaganie | Zrobione | Dowód plik:linia |
|---|---|---|
| P0.1 Transcript Guard (prawdziwy fallback) | TAK | pipeline.py:155 |
| P0.2 Playlista (idempotentnie config.PLAYLIST) | TAK | pipeline.py:317 |
| P0.3 YT z kontenera vse-api po config.YT_CHANNEL | TAK | pipeline.py:65 |
| P1.4 Idempotencja WP (YT ID i tytul L142-192 z B) | TAK | pipeline.py:237 |
| P1.5 step_verify (zapis do JSON per rekord) | TAK | pipeline.py:339 |
| P2.6 Testy (mock fallback, idempotencja YT/WP) | TAK | tests/test_biblia_worker.py:11 |
| N.7 --patch-meta (idempotent patch z wp term) | TAK | worker.py:100 (patch_meta) & pipeline.py:408 |

## NIE ZROBIONE / RYZYKA
brak

[media-dev]
