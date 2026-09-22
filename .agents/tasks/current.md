# current.md — media-dispatch

## ✅ Zamknięte

### Sesja 22.09.2026 — Naprawa YT Title+Desc & Shorts Candidates Diagnostic [media-dev-39]
- `agents/vse-worker/scripts/prawy_yt_fix_21_09_2026.py` (commit `8a76927b`):
  - Pipeline naprawczy YT title + description dla 6 filmów (Hsxu5L-27sU, vZAm46QIq84, -9y8AGJSNFs, lJLC8rqnlCs, PiwRUriZngc, J0Z1xMSqkls) z draftami WP #126808..#126833.
  - Generowanie live response z `POST /v1/generate` (pozyskanie `youtube_description_body`), pełny snippet YT z `title` i `description`, aktualizacja w kontenerze `vse-api` dla kanałów `Studio Prawy_PL` i `Prawy TV`.
- `agents/vse-worker/scripts/prawy_shorts_candidates_21_09_2026.py` (commit `20f4b9b9`):
  - Pipeline & skrypt diagnostyczny OpenAPI dla modułu Shorts (ekstrakcja `/v1/shorts/*`, pobranie schematów Pydantic, testowanie endpointu `POST /v1/shorts/candidates` dla 6 filmów).
- `.agents/knowledge/vse-worker-constitution.md` (commit `bc01353a`):
  - Sekcja 3: oznaczenie `/v1/youtube/publish-description` jako BROKEN dla kanałów Prawy.
  - Sekcja 11: zaktualizowany proces Short Machine do flow `candidates → render` i `describe`.
  - Sekcja 14: zastąpienie metody DB wzorcem live response Biblia (`youtube_description_body`, pełny snippet, `videos().list()` przed `update()`).
  - Sekcja 17 (NOWA): definicja aktywnych kanałów (`Studio Prawy_PL`, `Prawy TV`) oraz kanałów out of scope.
  - Sekcja 8: dodanie pułapek 19-21.

### Sesja 15.09.2026 — Full Flow Płużański
- `prawy_full_flow_pipeline.py` — artykuły VSE + YT opisy (commit 56df556b)
- `prawy_shorts_pipeline.py` — Short Machine generate + LocalRunner (commit 698c16cf)
- WP drafty: #126276 (Wołyń), #126281 (Pietrzak)
- YT opisy długich filmów: EWkRL1sEqQE + s6qif3Ed57E ✅
- Shorty w C:\VSE\Shorts\ gotowe do uploadu przez usera

### Faza 1 — Formalizacja prototypów (12.09.2026)
- `shorts-agent`, `pressai-worker`, `vse-worker`, `emisja-worker` — cd961dd...6e8471 [media-dev-A,B,C,D]

### Poprzednie sesje
- `transcribe-worker`: faster-whisper + VAD + CUDA + batch + dual PL/EN + --prompt (11.09.2026)
- Profil agenta: README + constitution + AGENTS.md (11.09.2026)

## 🟡 W toku
- Uruchomienie skryptów przez Supervisora w środowisku lokalnym:
  - `python agents/vse-worker/scripts/prawy_yt_fix_21_09_2026.py`
  - `python agents/vse-worker/scripts/prawy_shorts_candidates_21_09_2026.py`

## 🟢 Następne
- Analiza wyników `shorts_openapi_schema.json` i wykonanie zadań `POST /v1/shorts/render`
- Phase 3: user uploaduje shorty → agent podpina opisy YT (`process_shorts_describe.py`)
- Testy każdego workera (health_check + process dry_run)
