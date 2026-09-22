# current.md — media-dispatch

## ✅ Zamknięte

### Sesja 22.09.2026 — Naprawa YT Title+Desc & Shorts Candidates Diagnostic [media-dev-39]
- `agents/vse-worker/scripts/prawy_yt_fix_21_09_2026.py` (commit `8a76927b`):
  - Pipeline naprawczy YT title + description dla 6 filmów.
- `agents/vse-worker/scripts/prawy_shorts_candidates_21_09_2026.py` (commit `20f4b9b9`):
  - Pipeline & skrypt diagnostyczny OpenAPI dla modułu Shorts.
- `.agents/knowledge/vse-worker-constitution.md` (commit `bc01353a`):
  - Sekcja 3, 8, 11, 14, 17 — aktualizacje.

### Sesja 15.09.2026 — Full Flow Płużański
- `prawy_full_flow_pipeline.py` — artykuły VSE + YT opisy (commit 56df556b)
- `prawy_shorts_pipeline.py` — Short Machine generate + LocalRunner (commit 698c16cf)
- WP drafty: #126276 (Wołyń), #126281 (Pietrzak)
- YT opisy długich filmów: EWkRL1sEqQE + s6qif3Ed57E ✅
- Shorty w C:\\VSE\\Shorts\\ gotowe do uploadu przez usera

### Faza 1 — Formalizacja prototypów (12.09.2026)
- `shorts-agent`, `pressai-worker`, `vse-worker`, `emisja-worker` — cd961dd...6e8471

---

## 🟡 W toku

### Sesja 22.09.2026 — Thumbnail Generator Shorts [shorts-agent]

**Krok 1 — DONE** ✅ `thumbnail_generator.py` v11 (commit `7479658`)
- Layout 1:1 z PSD v11: granat apla #07152B, bez stroke, bg slot
- Font: NimbusSansNarrow-Bold, drop shadow, uniformny rozmiar
- Smart line grouping (1-3 słowa → każde osobno, 4+ → bloki 2)
- Slot `bg_path=` gotowy na AI-generated backgrounds (iteracja 2)
- Test produkcyjny: SADYSTKA BEZPIEKI + TORTUROWAŁA POLAKÓW ✅

**Krok 2 — NASTĘPNY** 🔵 Integracja z `worker.py`
- Przejrzeć `agents/shorts-agent/constitution.md` (istniejący pipeline)
- Zrozumieć gdzie worker wywołuje pipeline dla każdego Shorta
- Wpiąć `generate_thumbnail(video_id, hook_text, guest_text, cta_idx)` jako niezależny krok
- Cel: generator działa automatycznie — NIE każdorazowo ręcznie
- Sprawdzić skąd worker.py bierze hook_text i guest_text (VSE /v1/shorts/describe?)

**Krok 3 — ZAPLANOWANY** 🔵 Integracja z procesem publikacji
- Po pozytywnym teście kroku 2: wpięcie w pełen flow publikacji Shorts
- Zaplanować moment generowania klatki tła (bg slot) w procesie:
  - Kiedy? Przed publikacją, po transkrypcji, po describe?
  - Kto dostarcza bg: user manualnie (ręczny kadr) czy automatycznie z pliku wideo?
  - ffmpeg: extract frame z lokalnego .mp4 (~50% długości) jako default bg
  - Gotowe: ffmpeg 8.0 na lokalnym PC, pliki .mp4 w C:\\VSE\\Shorts\\

**Krok 4 — PRZYSZŁOŚĆ** 🔵 AI-generated backgrounds
- Dla słabych kadrów (rozmyte tło, brak kontaktu wzrokowego): AI generuje kontekstowe tło
- Slot `bg_path=` w `get_background()` gotowy — bez zmian w reszcie kodu
- Wymaga: wybór narzędzia (Flux/SDXL/Imagen), schemat promptów dla tematyki politycznej
- Nie blokuje kroków 2 i 3

---

## 🟢 Następne (poza thumbnail pipeline)
- Analiza wyników `shorts_openapi_schema.json` i wykonanie zadań `POST /v1/shorts/render`
- Phase 3: user uploaduje shorty → agent podpina opisy YT (`process_shorts_describe.py`)
- Testy każdego workera (health_check + process dry_run)
