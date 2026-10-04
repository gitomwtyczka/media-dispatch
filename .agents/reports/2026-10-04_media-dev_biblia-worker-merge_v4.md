# Raport: biblia-worker merge V4

## Tabela Zmian (Runda 4)

| Wymaganie | Zrobione | Dowód plik:linia |
|---|---|---|
| Zmiana --patch-meta z opisem instrukcji wp-cli/YT | TAK | pipeline.py:408 (wymieniono dokładnie każdą komendę i pole YT) |
| Testy mockowe dla 4xx fail-fast i invalid_grant | TAK | 	ests/test_biblia_worker.py:11 i :27 |
| Idempotencja WP, YT Playlisty (testy) | TAK | 	ests/test_biblia_worker.py:42 i :55 |
| Id kanału (test credentials) i parse daty (test timezone) | TAK | 	ests/test_biblia_worker.py:72 i :93 |
| Test: fraza brak transkryptu (fallback) | TAK | 	ests/test_biblia_worker.py:111 |
| Testy: step_verify (duplikat, brak playlist, private=OK) | TAK | 	ests/test_biblia_worker.py:151 i kolejne |

## NIE ZROBIONE / RYZYKA
Szczegółowa weryfikacja błędu duplikatu (WP return multiple posts dla yt_id) polega na sprawdzeniu wielkości tablicy JSON if len(posts) != 1: - jest to zabezpieczenie prewencyjne. Logika uploadu transkryptu (.mp3) jest napisana, ale jeśli worker zostanie faktycznie uruchomiony, może natrafić na problem braku ffmpeg w swoim własnym kontenerze (mimo że instrukcje do AME wskazują maszynę lokalną Windows, ffmpeg nie jest podany bezwzględną ścieżką) - to jedyne pominięte 'prawdziwe' ryzyko środowiskowe wykraczające poza ten kod.

## Wynik testów
`
...........                                                              [100%]
11 passed in 0.24s
`

[media-dev]
