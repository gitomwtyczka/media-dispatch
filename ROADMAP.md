# media-dispatch — ROADMAP v2.1
*Zaktualizowany: 2026-09-08 18:09 CEST | Supervisor 03*

---

## Wizja

media-dispatch to Content Operating System — system AI który bez ręcznej pracy zbiera tematy ze świata, ocenia ich ważność i produkuje gotowe treści (artykuły lub video) na portale.

---

## Architektura

```
SWIAT → WYWIAD → REDAKTOR NACZELNY → PRODUCENT → PORTAL
```

### Warstwa 1 — Wywiad
- **Feed Crawler** (`crawler.impresjapr.pl`) — 13 000+ RSS feedów — ✅ LIVE
- **Content Radar** (`radar.impresjapr.pl`) — trendy social media — ✅ LIVE (wymaga CONTENT_RADAR_JWT)
- **Gmail P0** — wiadomości od współpracowników — ✅ LIVE
- **GeoRelevanceSignal** — ważność PL/EU/Global — ✅ LIVE

### Warstwa 2 — Google Sheets (Human-in-the-Loop)
Arkusz ID: `1zqwvS784EaZh1EJIcXk1DliAau1r4X15ENFJjloDSaM`

| Zakładka | Portal | Worker (cron) | Status |
|----------|--------|---------------|--------|
| Emisja | prawy.pl | emisja_sheets_sync.py (co godz. :00) | ✅ LIVE |
| Propozycje Radar | prawy.pl | radar_sheets_sync.py (co godz. :30) | ✅ LIVE |
| Propozycje Kurier365 | kurier365.pl | kurier365_sheets_sync.py (co godz. :15) | ✅ LIVE |
| Propozycje BiznesCiti | biznesciti.com | biznesciti_sheets_sync.py (co godz. :45) | ✅ LIVE |
| Biblia | prawy.pl | ręczny (biblia_full_pipeline.py) | ✅ standalone |
| Shorty | prawy.pl | ręczny (process_shorts_describe.py) | ✅ standalone |
| Kandydaci YT | prawy.pl | prawy-youtube-worker | 🔴 planowane |

**Przepływ:**
1. Propozycje lądują automatycznie (feed-crawler co 6h) lub manualnie
2. Użytkownik wpisuje `Publikuj w PressAI` lub `Publikuj VSE` w kolumnie Status
3. Skrypt sync generuje artykuł przez PressAI lub video przez VSE → WP Draft

### Warstwa 3 — Producenci
- **PressAI** (`press.impresjapr.pl`) — artykuły tekstowe → WP Draft — ✅ LIVE
- **VSE** (`vse.impresjapr.pl`) — video YouTube → WP Draft + opis YT — ✅ LIVE

### Standalone Workers (nie przez orkiestrację)
- `prawy-studio-worker` — video Studio Prawy_PL (VSE pipeline) — ✅ MVP v1.0
- `prawy-youtube-worker` — monitoring kanału YT — ✅ v1.0 skeleton
- `agents/vse-worker/scripts/biblia_*.py` — Prawy Biblijny (audio → VSE) — ✅ standalone

---

## Stan wdrożenia (08.09.2026 18:00 CEST)

### ✅ DZIAŁA
- Feed Crawler source — 13k+ RSS, zbiera kandydatów
- Gmail source — priorytet P0, współpracownicy
- GeoRelevanceSignal — scoring ważności
- ContentRadarSignal — aktywny po podaniu CONTENT_RADAR_JWT
- `kurier365-worker` — zbieranie + routing do Sheets (cron co 6h)
- Google Sheets — 6 zakładek, sync scripts dla 3 portali
- Sheets → PressAI sync — artykuły na żądanie (cron co godz.)
- SA `media-dispatch-sheets@...` — autoryzacja Sheets → VPS
- Portal UUIDs: KURIER365_PORTAL_ID, BIZNESCITI_PORTAL_ID (w .env)
- `prawy-studio-worker` — standalone, VSE pipeline z checkpointing
- `prawy-youtube-worker` — standalone, monitoring kanału
- Biblia scripts — standalone, pelny audio → VSE pipeline

### 🔴 DO ZBUDOWANIA (priorytety)

**PRIORYTET 1: Detekcja video w Sheets sync**
Dodanie obsługi `Publikuj VSE` w radar/kurier365/biznesciti sync scripts.
Wzór: `emisja_sheets_sync.py` (YT URL → VSE pipeline).

**PRIORYTET 2: CONTENT_RADAR_JWT**
Pobrać token z panelu `radar.impresjapr.pl` → dodać do `.env`.
Efekt: trendy social media zasilają scoring kandydatów.

**PRIORYTET 3: Biblia worker — przeniesienie do repo**
`agents/vse-worker/scripts/biblia_*.py` istnieje tylko lokalnie.
Należy dodać jako `agents/biblia-worker/` do repo GitHub.

**PRIORYTET 4: Redaktor Naczelny MVP**
Agent który co godzinę bierze top kandydatów z feed-crawlera + Content Radaru
i wrzuca do właściwej zakładki Sheets automatycznie.
Routing: biznes → BiznesCiti, nauka/geopolityka → Kurier365, polityka/KK → prawy

**PRIORYTET 5: shorts-agent (implementation)**
Spec gotowa, zero kodu. Shorts Machine API dostępne od 31.08.2026.

**ODROCZONE:**
- Discord Editorial Center (Faza 3)
- TikTok worker (Faza 6)
- Multi-platform distribution (Faza 6)

---

## Crontab VPS (aktualny — 08.09.2026)

```bash
0  */6 * * *  kurier365-worker/worker.py --run --sheets   # zbieranie + Sheets
0  * * * *    emisja_sheets_sync.py                       # Emisja → VSE
30 * * * *    radar_sheets_sync.py                        # Radar → PressAI prawy.pl
15 * * * *    kurier365_sheets_sync.py                    # Kurier365 → PressAI
45 * * * *    biznesciti_sheets_sync.py                   # BiznesCiti → PressAI
```

---

## Portal UUIDs (vse-postgres.wp_portals)

| Portal | UUID |
|--------|------|
| prawy.pl | `2b047d7d-15a1-4d2f-8463-f89c2275bb73` |
| kurier365.pl | `dc49d944-188a-4e64-8465-f0a5d6a0221a` |
| biznesciti.com | `3bf77e55-26ba-4f0b-b7dc-a79d91d2f4b1` |

---

## Service Account

- SA email: `media-dispatch-sheets@antigravity-mcp-keys.iam.gserviceaccount.com`
- SA path VPS: `/home/ubuntu/media-dispatch/config/service_account.json`
- Env var: `GOOGLE_SA_FILE`

---

## Standardy techniczne

### Task schema (Redaktor Naczelny → Producenci)
```json
{
  "task_id": "uuid",
  "type": "pressai|vse",
  "portal_id": "prawy|kurier365|biznesciti",
  "source_url": "https://...",
  "source_type": "article|youtube",
  "priority": 1,
  "scheduled_at": "ISO timestamp",
  "created_by": "redaktor-naczelny|user"
}
```

### Agent interface
```python
def health_check() -> bool
def process(task) -> result
def get_status() -> WorkerStatus
```

---

*[Supervisor 03 | sonic-void 08.09.2026] — ROADMAP v2.1 — pełny stan po sesji 3*
