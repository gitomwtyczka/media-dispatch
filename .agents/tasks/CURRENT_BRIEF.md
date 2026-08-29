# media-dispatch — CURRENT BRIEF

> Ostatnia aktualizacja: 2026-08-30 | Supervisor 01
> Następna sesja startuje W TYM WORKSPACE: `media-dispatch`

---

## Stan po sesji 29-30.08.2026

### ✅ Zrealizowane
- 7 filmów biblijnych (30.08–05.09.2026) przetworzonych przez VSE
- Transkrypcja Whisper → napisy VTT → wgrane na YouTube
- YouTube: opisy, scheduledPublishAt 00:00, playlista Ewangelia
- prawy.pl: 7 zaplanowanych postów z thumbnail, YouTube embed, alt text
- Konstytucja workera: `.agents/knowledge/vse-worker-constitution.md`
- Prawidłowy flow: `agents/vse-worker/scripts/biblia_full_pipeline.py`

### ⚠️ Do zrobienia w następnej sesji
- [ ] Napisy VTT dla filmów 28.08 i 29.08 (ignorowane w tej sesji)
- [ ] Weryfikacja postów na prawy.pl (sprawdzić schema VideoObject w source)
- [ ] Prawy TV standard pipeline do zaimplementowania (patrz sekcja Architektury)

---

## ARCHITEKTURA — DWA PIPELINY

### Pipeline A — Prawy Biblijny (kanał bez auto-napisów YT)

YouTube nie rozpoznaje języka PL na tym kanale → brak auto-captions.
Whisper jest WYMAGANY.

```
Krok 1: MP3 → POST /v1/audio/generate → VTT
Krok 2: VTT → YouTube captions.insert (wgranie napisów)
Krok 3: [czekaj 30s] → POST /v1/generate z URL YouTube
         (teraz YT ma napisy → VSE: thumbnail ✅ + VideoObject ✅ + embed ✅)
Krok 4: schema → POST /v1/inject → WP post zaplanowany
Krok 5: videos.update → tytuł SEO + opis + scheduledPublishAt
Krok 6: playlistItems.insert → playlista
```

Skrypt: `agents/vse-worker/scripts/biblia_full_pipeline.py`

### Pipeline B — Prawy TV (kanał z auto-napisami YT)

YouTube wykrywa język PL i generuje auto-captions.
Whisper NIE jest potrzebny.

```
Krok 1: POST /v1/generate z URL YouTube
         (VSE czyta auto-captions z YT → pełne SEO)
Krok 2: POST /v1/inject → WP post + publikacja na prawy.pl
Krok 3: videos.update → opis YouTube (z schema_data)
```

Skrypt: `agents/vse-worker/scripts/prawy_standard_pipeline.py` (DO STWORZENIA)

---

## INFRASTRUKTURA VSE — skrót

| Element | Wartość |
|---------|--------|
| API URL | `https://vse.impresjapr.pl` |
| Port wewnętrzny | 8085 |
| SSH | `ubuntu@147.224.162.100`, klucz `C:\Users\tomas2\.ssh\oracle-crimson.key` |
| JWT | `jose.jwt.encode()` w `vse-api` container |
| Konto | `tobroz@gmail.com` (ID: 4b97ab0c-98ee-46c6-9be8-d86adc4cb38a) |
| Portal WP | `prawy` |

> Pełna wiedza: `.agents/knowledge/vse-worker-constitution.md`

---

## KANAŁY YOUTUBE

| Kanał | Typ | Pipeline | Playlista |
|-------|-----|----------|-----------|
| Prawy Biblijny | Biblia codziennie ~8 min | Pipeline A (Whisper) | `PLw7UeigJuyWkUzzvhS1vZX0H251raaYa7` |
| Prawy TV | Wywiady, komentarze | Pipeline B (bez Whisper) | — |

---

## UWAGA DLA NASTĘPNEGO AGENTA

1. Startuj w workspace `media-dispatch` (repo: `gitomwtyczka/media-dispatch`, branch: `main`)
2. Przeczytaj `.agents/knowledge/vse-worker-constitution.md` PRZED jakimkolwiek działaniem
3. Heartbeat na starcie: `.agents/heartbeat.json` w media-dispatch
4. Raporty dual-write: `media-dispatch/.agents/reports/` + `sonic-void/.agents/reports/inbox/`
5. Wszystkie pliki projektowe przez GitHub MCP (nie write_to_file na lokalnym klonie)
6. Tytuły YT ZAWSZE aktualizuj razem z opisem (videos.update?part=snippet wymaga obu pól)