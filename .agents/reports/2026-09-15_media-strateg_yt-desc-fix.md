# YT Description Fix Report — 15.09.2026

## Problem
- YT opisy były stubami (meta_description zamiast pełnego opisu z VSE)
- Pietrzak: brak transkryptu → AI nazmyslał (post #126281 usunięty)

## Rozwiązanie

### Transcript guard
- `/v1/generate` zwraca `transcript_available: bool` w response
- Jeśli `False` → STOP, nie inject, warn
- Pietrzak miał transkrypt później (ok. 30 min) → retry zakończony sukcesem

### YT opis — odkrycia
- `publish-description` sprawdza właściciela wideo → nie działa dla kanałów zarządzanych pośrednio
- Właściwa metoda: skrypt `yt_desc_fix.py` w kontenerze `vse-api` z `videos.update()` przez konto Tomasz Brzozowski
- Schema_data w DB: tabela `transcript_jobs`, kolumna `video_url`, pola: `lead`, `chapters`, `tags`

### Wyniki końcowe

| Film | YT ID | WP | YT opis |
|------|-------|-----|--------|
| Płużański Popek Wołyń 1 | EWkRL1sEqQE | [#126276](https://prawy.pl/?p=126276) (draft) | ✅ poprawiony |
| Płużański Pietrzak | s6qif3Ed57E | [#126295](https://prawy.pl/?p=126295) (draft) | ✅ poprawiony |
| Pietrzak hallucynacja | s6qif3Ed57E | #126281 | USUNIĘTY |

## Skrypty
- `prawy_full_flow_v2.py` — główny pipeline z transcript guardem
- `prawy_shorts_pipeline.py` — Short Machine generate + LocalRunner
- `yt_desc_fix.py` — naprawa YT opisu wewnątrz kontenera vse-api