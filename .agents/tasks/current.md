# current.md — media-dispatch

## ✅ Zamknięte

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
- Rotacja sekretów (4 wycieki w brain scratch: JWT, GitHub token, WP password, PRESSAI_JWT)

## 🟢 Następne
- Phase 3: user uploaduje shorty → agent podpina opisy YT (`process_shorts_describe.py`)
- Testy każdego workera (health_check + process dry_run)
- Documetacja: Grand Unified, Tutorial, SRT-Driven (Faza 2)
