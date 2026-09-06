# Raporty Analityczne — Sesja 2026-09-06

> Wygenerowane przez subagentów podczas sesji ebc94408. Do odczytania przez następną sesję.

---

# RAPORT A: Strategia & Architektura (sup-analyst-01)

## 1. Co jest eleganckie i trafione

- **Sheets-Driven Cockpit** → eliminacja przepalania tokenów na zatwierdzanie, redaktor klika kiedy chce, z telefonu, offline
- **3 niezależne potoki** (Biblia / Emisja / Radar) — izolacja domen, Biblia już produkcyjna, reszta się domyka
- **Cron headless na VPS** — egzekucja niezależna od sesji IDE

## 2. Co jest koślawe i nadmiarowe

- **Sheets jako transakcyjna kolejka** — arkusz nie jest kolejką ACID. Sortowanie przez redaktora w trakcie 4-minutowego generowania LLM = race condition i update złego wiersza
- **SSH-do-samego-siebie** — skrypt działający na VPS robi `ssh ubuntu@147.224.162.100 docker exec ...` przez sieć publiczną! Relikt przenoszenia z Windowsa
- **Hardcoded row offsets** — `row[0]`, `row[2]`, `row[7]` zamiast mapowania po nagłówkach. Jedna nowa kolumna dodana przez redaktora = crash

## 3. Miny (Single Points of Failure)

| # | Mina | Skutek |
|---|---|---|
| 💥1 | SSE parsowane jako JSON (`r_gen.json()`) | Artykuły nigdy nie powstają, Cron kręci się w pętli błędów |
| 💥2 | Ścieżki Windows hardcoded na Linux VPS | `FileNotFoundError` przy każdym uruchomieniu z Crona |
| 💥3 | Brak blokady współbieżności | Podwójne publikacje przy nakładaniu się Cronów |
| 💥4 | Statyczny JWT w `.env` | Gdy wygaśnie — WSZYSTKIE workery padają jednocześnie z 401 |
| 💥5 | `SHEET_ID` rozbieżne między plikami | Crawler pisze w próżnię, redakcja nie widzi newsów |

## 4. Quick Wins (wdrożyć natychmiast)

1. **Fix SSE:** `r_gen.iter_lines()` + strip `data:` prefix + szukaj `chunk["result"]["generated_article"]`
2. **Fix ścieżek:** `GOOGLE_SA_KEY_PATH` w `.env`, wgrać właściwy SA na VPS do `/home/ubuntu/media-dispatch/config/`
3. **Mapowanie kolumn po nazwach** zamiast indeksów: `col_idx = {name.lower().strip(): i for i, name in enumerate(rows[0])}`
4. **Bramka atomowa:** przed wywołaniem PressAI → natychmiast zmień status na `"Przetwarzanie..."` (anti-double-publish)

## 5. Priorytety Stabilizacji

- `flock` na Cronie (zapobiega nakładaniu się procesów)
- Automatyczne odświeżanie JWT lub Machine API Key dla workerów
- Kolumny zwrotne w arkuszu: `Link do szkicu WP` + `Log błędu` (widoczność dla redaktora co poszło nie tak)

---

# RAPORT B: Audyt Techniczny + Shorts Worker (research-01)

## Shorts Worker — gdzie jest?

### `agents/shorts-agent/` — SZKIELET (tylko README, brak kodu .py)
- Projektowany do YT Data API v3 + Short Machine API (`POST /v1/shorts/describe`)
- Brak integracji z Google Sheets
- Harmonogram: plik JSON `shared/schedules/shorts_schedule.json`
- CLI: `--scan`, `--schedule`, `--upload-tiktok`

### `agents/prawy-studio-worker/` — PEŁNY KOD (worker.py 23.5KB)
- **To jest główny worker shortów — tu jest cały pipeline!**
- Pełny flow: JWT → check captions → VSE generate → inject WP → YT description → shorts candidates → shorts render
- `--shorts-only YOUTUBE_ID` — tryb dedykowany
- Output do `C:\VSE\Shorts` (Windows path!)
- **Brak integracji z Google Sheets** — stan w lokalnym `batch_progress.json`

## Audyt Kodu — Checklist

| Punkt | `radar_sheets_sync.py` | `kurier365-worker/worker.py` |
|---|---|---|
| SSE `iter_lines` + `data:` strip | ❌ Brak — używa `r_gen.json()` | ⚠️ Częściowy strip ale bez `iter_lines` |
| Zakładka `Propozycje Radar` | ✅ OK | ❌ Nadal pisze do `Kandydaci` |
| Linux path SERVICE_ACC | ❌ Windows path `C:\Users\tomas2...` | ✅ `/home/ubuntu/otwock-data/muzeum/...` |
| SHEET_ID `1zqwvS78...` | ✅ OK | ❌ Stary testowy `1HMuODAI...` |

**Wniosek:** Worker Deployera, który właśnie pracuje, ma w swoim Dispatchu te poprawki. Gdy skończy — ZWERYFIKUJ przez GitHub MCP czy plik w repo jest naprawdę zaktualizowany, a nie tylko na VPS.

---

## Rekomendacja dla Następnej Sesji

1. **Odbierz raport od aktywnego Workera Deployera** — sprawdź czy SSE i SHEET_ID zostały naprawione
2. **Uruchom test end-to-end** przez SSH na VPS
3. **Zaplanuj formalizację `prawy-studio-worker`** — integracja z zakładką `Shorty` w Excelu (podobny wzorzec jak Emisja)
4. **Rozważ wgranie dedykowanego SA** zamiast `muzeum-drive-sa.json`

---

*Raporty wygenerowane: 2026-09-06 21:36 | sesja ebc94408*
