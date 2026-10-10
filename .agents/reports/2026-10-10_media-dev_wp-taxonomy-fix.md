# Raport: Naprawa taksonomii i weryfikacji WP-CLI
**Data:** 2026-10-10
**Callsign:** media-dev (Worker)
**Cel:** Naprawa 7 wpisów w WP i logiki pipeline'u.

## 1. Zmiany na produkcji (WordPress VPS)
Zaktualizowano wpisy o ID: 127909, 127914, 127918, 127925, 127930, 127935, 127940.
Wykonano:
- `wp post term set <id> podcast_show prawy-biblijny`
- `wp post term set <id> category biblia` (czyszcząc "Uncategorized" itp.)
- `wp post meta update <id> podcast_youtube_url '...'`
Statusy (future) oraz daty (11-17.10) zachowane, post_content nietknięty. YouTube nie był dotykany zgodnie z instrukcją. 
Ominięto wpisy z batcha 04-10.10.

## 2. Zmiany w kodzie (media-dispatch: agents/biblia-worker/pipeline.py)
**Analiza przyczyny:** W `step_wpcli` używano instrukcji `wp post term add`, która nie usuwała innych przypisanych wcześniej terminów (np. Uncategorized) oraz dla niektórych przypadków zawodziła. W logice testów brakowało też weryfikacji treści wpisu.
**Rozwiązanie:** 
- Zmieniono `term add` na `term set` dla `podcast_show` oraz `category`.
- Wzbogacono `step_verify` (po stronie sprawdzającej WP) o weryfikację ścisłą (`['biblia']` i `['prawy-biblijny']`) oraz sprawdzanie czy `post_content` (pole `content.rendered` z API WP) nie jest puste.
- Dodano mock `content` w teście. Kod poprawnie przechodzi `pytest` i `py_compile`. Skommitowano na branch `main`.

## 3. Wynik weryfikacji po poprawkach
| Wpis | Status | Data | Kategorie | Podcast Show | Meta YT | Treść |
|---|---|---|---|---|---|---|
| 127909 | future | 2026-10-11 00:00:00 | [biblia] (TAK) | prawy-biblijny (TAK) | TAK | TAK (16315 znaków) |
| 127914 | future | 2026-10-12 00:00:00 | [biblia] (TAK) | prawy-biblijny (TAK) | TAK | TAK (15383 znaków) |
| 127918 | future | 2026-10-13 00:00:00 | [biblia] (TAK) | prawy-biblijny (TAK) | TAK | TAK (15830 znaków) |
| 127925 | future | 2026-10-14 00:00:00 | [biblia] (TAK) | prawy-biblijny (TAK) | TAK | TAK (16241 znaków) |
| 127930 | future | 2026-10-15 00:00:00 | [biblia] (TAK) | prawy-biblijny (TAK) | TAK | TAK (16029 znaków) |
| 127935 | future | 2026-10-16 00:00:00 | [biblia] (TAK) | prawy-biblijny (TAK) | TAK | TAK (14516 znaków) |
| 127940 | future | 2026-10-17 00:00:00 | [biblia] (TAK) | prawy-biblijny (TAK) | TAK | TAK (16450 znaków) |

## NIE ZROBIONE / RYZYKA
- Puste szkice (127835, 127762, 127520) nie zostały usunięte ani zmodyfikowane.
- Skrypt weryfikujący (PHP w SSH) wypisuje "Deprecated: WPMailSMTP... nullable type must be used instead in...", co zanieczyszczało JSONy podczas pobierania list terminów z CLI przez --format=json. Przefiltrowano dla raportu, jednak ten Warning istnieje globalnie w WP instalacji i może powodować awarię niektórych parsowań API/CLI jeśli nie jest maskowany.
