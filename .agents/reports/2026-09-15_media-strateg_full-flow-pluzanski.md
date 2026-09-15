# Full Flow Report: Płużański Popek Wołyń 1 + Płużański Pietrzak

Data: 2026-09-15 | Agent: media-strateg | media-dev-A1, B2, C1

## ✅ Phase 1 — VSE Articles + YouTube Descriptions

| Film | YT ID | WP Post | YT Opis |
|------|-------|---------|--------|
| Płużański Popek Wołyń 1 | EWkRL1sEqQE | [#126276](https://prawy.pl/?p=126276) (draft) | ✅ |
| Płużański Pietrzak | s6qif3Ed57E | [#126281](https://prawy.pl/?p=126281) (draft) | ✅ |

Skrypt: `agents/vse-worker/scripts/prawy_full_flow_pipeline.py` (commit 56df556b)

## ✅ Phase 2 — Shorts Generation

Short Machine wygenerował 10 kandydatów per film (5 emotional + 5 professional).
Local Runner (VSELocalRunner Windows Service) pociął klipy z lokalnych MP4.
Pliki wylądowały w `C:\VSE\Shorts\`.

| Film | Kandydaci | Status |
|------|-----------|--------|
| Płużański Popek Wołyń 1 | 10 (5+5) | ✅ wycięte |
| Płużański Pietrzak | 10 (5+5) | ✅ wycięte |

Skrypt: `agents/vse-worker/scripts/prawy_shorts_pipeline.py` (commit 698c16cf)

## 🟡 Phase 3 — następna sesja

User uploaduje shorty na YouTube manualnie.
Następny agent: `process_shorts_describe.py` → opisy + pinned comments przez YT API.

## Odkrycia operacyjne

1. **Workery background nie mogą run_command** — timeout approval. Pattern: worker pisze skrypt → supervisor uruchamia lokalnie.
2. **subprocess + polskie znaki**: używaj `capture_output=True` (bez `text=True`) + `.decode('utf-8', errors='replace')`
3. **Short Machine endpoint**: `POST /v1/shorts/generate` z `count_emotional` + `count_professional`
4. **local_overrides.json**: `C:\ProgramData\VSELocalRunner\local_overrides.json` — mapuje YT ID → lokalny MP4
5. **VSELocalRunner** działa jako Windows Service — polluje `/v1/shorts/pending` co 5s
