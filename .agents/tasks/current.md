# current.md — media-dispatch

## ✅ Zamknięte

### Faza 1 — Formalizacja prototypów (12.09.2026)
- `shorts-agent`: `worker.py` + `scheduler.py` + `README.md` + `constitution.md` — cd961dd, da39de2, f328313, 58fa9d4 [media-dev-A]
- `pressai-worker`: `auto_publisher.py` + `worker.py` + `README.md` + `constitution.md` — 9612364, 488fde4, 8baf6cc, 8d73de1 [media-dev-B]
- `vse-worker`: `pipeline.py` + `worker.py` + `README.md` + `constitution.md` — 7f0ed34, ad738a0, bc7732f, 62dfcf1 [media-dev-C]
- `emisja-worker`: `collab_linker.py` + `worker.py` + `README.md` + `constitution.md` — 9808e4a, 6e8471 [media-dev-D]

### Poprzednie sesje
- `transcribe-worker`: faster-whisper + VAD + CUDA + batch + dual PL/EN + --prompt (11.09.2026)
- Profil agenta: README + constitution + AGENTS.md (11.09.2026)
- Pełna archeologia: 106 sesji brain, ~90 niesformalizowanych skryptów (11.09.2026)

## 🟡 W toku
- Rotacja sekretów (4 wycieki w brain scratch: JWT, GitHub token, WP password, PRESSAI_JWT)

## 🟢 Następne
- Testy każdego workera (health_check + process dry_run)
- --extract-text do transcribe.py (30 min, odblokowuje PressAI pipeline end-to-end)
- Constitutions dla kurier365, prawy-studio, prawy-youtube
- Dokumentacja architektoniczna: Grand Unified, Tutorial, SRT-Driven (Faza 2)
- Formalizacja pozostałych Tier 1: `auto_prawy.py`, `monitor_sync.py`, `find_streams.py` (Faza 1b)
