# media-dispatch — ROADMAP v2.0
*Zaktualizowany: 2026-09-08 | Supervisor 03*

---

## Wizja

media-dispatch to Content Operating System — system AI który bez ręcznej pracy zbiera tematy ze świata, ocenia ich ważność i produkuje gotowe treści (artykuły lub video) na portale.

---

## Architektura

```
SWIAT → WYWIAD → REDAKTOR NACZELNY → PRODUCENT → PORTAL
```

### Warstwa 1 — Wywiad (Intelligence)
Automatycznie zbiera i ocenia tematy:
- **Feed Crawler** (`crawler.impresjapr.pl`) — 13 000+ RSS feedów, świat i Polska
- **Content Radar** (`radar.impresjapr.pl`) — trendy social media (Twitter/X, YT, TikTok, Google Trends)
- **Gmail P0** — wiadomości od współpracowników (Rudiński, Binćzyk, Żabka i in.)
- **GeoRelevanceSignal** — ważność PL/EU/Global

### Warstwa 2 — Redaktor Naczelny (Editorial AI)
Meta-agent który:
1. Zbiera raporty od wywiadu
2. Segreguje propozycje per portal (prawy.pl / kurier365.pl / biznesciti.com)
3. Wrzuca do Google Sheets (zakładka per portal)
4. Po zatwierdzeniu przez użytkownika → dispatch do producenta

### Warstwa 3 — Producenci
- **PressAI** (`press.impresjapr.pl`) — generuje artykuły tekstowe → WP Draft
- **VSE** (`vse.impresjapr.pl`) — przetwarza video YouTube → WP Draft + opis YT

### Workers samodzielne (poza orkiestracją Redaktora)
- `prawy-studio-worker` — video Studio Prawy_PL (standalone)
- `prawy-youtube-worker` — kanał YT Studio Prawy_PL (standalone)
- `biblia-worker` — [do potwierdzenia]

---

## Google Sheets — przepływ propozycji

Arkusz: `1zqwvS784EaZh1EJIcXk1DliAau1r4X15ENFJjloDSaM`

| Zakładka | Portal | Sync script (cron) |
|----------|--------|--------------------|
| Propozycje Radar | prawy.pl | `radar_sheets_sync.py` (:30 co godz.) |
| Propozycje Kurier365 | kurier365.pl | `kurier365_sheets_sync.py` (:15 co godz.) |
| Propozycje BiznesCiti | biznesciti.com | `biznesciti_sheets_sync.py` (:45 co godz.) |

**Sposób działania:**
1. Propozycje lądują automatycznie (feed-crawler) lub manualnie
2. Użytkownik wpisuje `Publikuj w PressAI` lub `Publikuj VSE` w kolumnie Status
3. Skrypt sync generuje artykuł przez PressAI lub video przez VSE → WP Draft

---

## Stan wdrożenia (08.09.2026)

### DZIAŁA ✅
- Feed Crawler source (FeedCrawlerSource) — 13k+ RSS
- Gmail source (GmailSource) — priorytet P0
- GeoRelevanceSignal — ważność geograficzna
- ContentRadarSignal — żywy gdy CONTENT_RADAR_JWT ustawiony
- `kurier365-worker` — zbieranie kandydatów, routing do Sheets
- `prawy-studio-worker` — standalone, video
- `prawy-youtube-worker` — standalone, YT
- Google Sheets — 3 zakładki propozycji (wdrożone 08.09.2026)
- Sheets → PressAI sync — artykuły generowane automatycznie (wdrożone 08.09.2026)
- Portal UUIDs w `.env`: KURIER365_PORTAL_ID, BIZNESCITI_PORTAL_ID (wdrożone 08.09.2026)

### DO ZBUDOWANIA 🔴

**PRIORYTET 1: Detekcja video w Sheets sync**
- Jeśli URL = YouTube (`youtube.com` / `youtu.be`) → VSE zamiast PressAI
- Dotyczy: `radar_sheets_sync.py`, `kurier365_sheets_sync.py`, `biznesciti_sheets_sync.py`

**PRIORYTET 2: Redaktor Naczelny MVP**
- Agent który co godzinę bierze top kandydatów z feed-crawlera + Content Radaru
- Wrzuca propozycje do właściwej zakładki Sheets automatycznie
- Routing: biznes/gospodarka → BiznesCiti, nauka/geopolityka → Kurier365, polityka/KK → prawy
- Po zatwierdzeniu przez użytkownika → dispatch do PressAI lub VSE

**PRIORYTET 3: CONTENT_RADAR_JWT**
- Pobrać token z panelu `radar.impresjapr.pl`
- Dodać do `.env` na VPS
- Efekt: trendy social media zaczną automatycznie wpływać na scoring kandydatów

**PRIORYTET 4: pressai-worker (ujednolicony)**
- Refaktor 3 osobnych skryptów sync do jednego modułu w `agents/pressai-worker/`
- Niższy priorytet — funkcjonalnie działa już w obecnej formie

**ODROCZONE:**
- Discord Editorial Center (Faza 3)
- shorts-agent + TikTok worker (Faza 6)
- Multi-platform distribution (Faza 6)

---

## Crontab VPS (aktualny stan)

```bash
0  */6 * * *  kurier365-worker/worker.py --run --sheets    # zbieranie kandydatów
0  * * * *    emisja_sheets_sync.py                        # Emisja zakładka
30 * * * *    radar_sheets_sync.py                         # Radar → prawy.pl
15 * * * *    kurier365_sheets_sync.py                     # Kurier365 sync
45 * * * *    biznesciti_sheets_sync.py                    # BiznesCiti sync
```

---

## Portal UUIDs (vse-postgres.wp_portals)

| Portal | UUID |
|--------|------|
| prawy.pl | `2b047d7d-15a1-4d2f-8463-f89c2275bb73` |
| kurier365.pl | `dc49d944-188a-4e64-8465-f0a5d6a0221a` |
| biznesciti.com | `3bf77e55-26ba-4f0b-b7dc-a79d91d2f4b1` |

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
Każdy worker musi implementować:
- `health_check()` → bool
- `process(task)` → result
- `get_status()` → WorkerStatus
