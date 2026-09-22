# HANDOFF — media-strateg | 22.09.2026 18:43

## ⚠️ PRIORYTET 0 — WERYFIKACJA BRAIN PRZED DZIAŁANIEM

Przed wykonaniem jakichkolwiek kroków: przeanalizuj brain poprzedniej sesji.

**Conversation ID:** `dc4d771a-34f6-4b0d-ad88-6a3ffd47e8cf`  
**Transcript:** `C:\Users\tomas2\.gemini\antigravity\brain\dc4d771a-34f6-4b0d-ad88-6a3ffd47e8cf\.system_generated\logs\transcript.jsonl`

**Co zweryfikować:**
1. YT update Urbaniak (`BsmvkNqRGRU`) — czy naprawdę zakończyło się `OK: BsmvkNqRGRU via Studio Prawy_PL` (task-299 lub finalna komenda)?
2. WP draft — worker `40b0fcdd` — jaki był jego output? Czy WP ID istnieje?
3. Shorts Urbaniak — 10 jobów QUEUED — czy Local Runner potwierdził przetworzenie?
4. Shorty 21.09 (59 jobów) — czy user potwierdził że są na dysku w `C:\VSE\Shorts\`?
5. generate-srt 429 — które dokładnie filmy mają SRT a które nie?

**Pliki wynikowe do sprawdzenia lokalnie:**
- `C:\Users\tomas2\.gemini\antigravity\brain\urbaniak_generate_response.json`
- `C:\Users\tomas2\.gemini\antigravity\brain\urbaniak_pipeline_results.json`
- `C:\Users\tomas2\.gemini\antigravity\brain\shorts_candidates_results.json`

**Strategia:** task logi w `.system_generated/tasks/task-*.log` zawierają rzeczywiste outputy komend — to jest źródło prawdy, nie deklaracje w handoffie.

Powod: V1:Flash 80+ RED + dryf kompetencji (strateg implementowal zamiast delegowac do workera)

## CO ZROBIONE

### Filmy 21.09 (6 filmow) - KOMPLETNE
Hsxu5L-27sU | WP #126808 | YT OK
vZAm46QIq84 | WP #126813 | YT OK
-9y8AGJSNFs | WP #126818 | YT OK
lJLC8rqnlCs | WP #126823 | YT OK
PiwRUriZngc  | WP #126828 | YT OK
J0Z1xMSqkls | WP #126833 | YT OK
Shorty 21.09: 59 jobów QUEUED, pociete widoczne w C:\VSE\Shorts

### Film 22.09 - Pluzanski Michal Urbaniak (BsmvkNqRGRU)
- YT title+desc: OK via Studio Prawy_PL
- WP draft: BLOKER
- Shorts candidates: 10 OK
- Shorts render: 10 QUEUED
- generate-srt: 429 bug VSE

### Konstytucja VSE workera
Commit: d09fee96 - pulapki 22-26, AME log sekcja, generate-srt kolejnosc

## BLOKERY

### WP draft Urbaniak - NIE stworzony
Root cause: pierwsze /v1/generate wywolane bez publication_type+llm_provider -> local_fallback w cache.
VSE przy local_fallback nie tworzy WP draft.
Rozwiazanie: DELETE FROM transcript_jobs WHERE video_url ILIKE '%BsmvkNqRGRU%'
Potem POST /v1/generate z: video_url, portal_id, publication_type=full_analysis, llm_provider=claude
Worker dispatched: 40b0fcdd-377f-4cfc-8283-daea9d622371 - sprawdz czy skonczyl!

### generate-srt 429 bug
Filmy bez SRT: -9y8AGJSNFs, lJLC8rqnlCs, PiwRUriZngc, J0Z1xMSqkls, BsmvkNqRGRU
Bug: VSE zwraca 429 mimo plan_id=agency, is_admin=true
Nie bloker dla shortow (juz pociete)

## WIEDZA KRYTYCZNA

YT update WLASCIWY wzorzec (z prawy_yt_fix_21_09_2026.py - commit 8a76927b):
- youtube_channel_id (NIE channel_id!)
- is_active == True
- docker cp /tmp/s.py vse-api:/app/s.py (NIE /tmp/!)
- docker exec -w /app vse-api python3 s.py

/v1/generate - ZAWSZE:
- video_url (NIE youtube_url)
- publication_type: full_analysis
- llm_provider: claude
- portal_id

## INFRASTRUKTURA
VPS: ubuntu@147.224.162.100
SSH KEY: C:\Users\tomas2\.ssh\oracle-crimson.key
VSE: https://vse.impresjapr.pl port 8085
PORTAL_ID: 2b047d7d-15a1-4d2f-8463-f89c2275bb73
USER_ID (tobroz@gmail.com): 4b97ab0c-98ee-46c6-9be8-d86adc4cb38a
AME log: C:\Users\tomas2\Documents\Adobe\Adobe Media Encoder\26.0\AMEEncodingLog.txt (utf-16-le)
local_overrides: C:\ProgramData\VSELocalRunner\local_overrides.json
Shorts output: C:\VSE\Shorts

KANALY:
Studio Prawy_PL: UCoH2G9By4OX3kcLsc8lHgDw (primary)
Prawy TV: UCNXh5eIlMVxnUBpTMKUp4CA
Tomasz Brzozowski, VeriNarrMundo: OUT OF SCOPE

BRAIN:
C:\Users\tomas2\.gemini\antigravity\brain\dc4d771a-34f6-4b0d-ad88-6a3ffd47e8cf\ - skrypty sesji
urbaniak_generate_response.json - pelny /v1/generate response
Conversation ID: dc4d771a-34f6-4b0d-ad88-6a3ffd47e8cf

NASTEPNE KROKI:
1. Sprawdz workera 40b0fcdd - czy WP Urbaniak gotowy
2. Jesli nie: DELETE cache + re-generate
3. generate-srt bug: naprawa VSE
4. Opisy shortow: gdy user wgra - process_shorts_describe.py
