# AGENTS.md — media-dispatch

Reguły specyficzne dla workspace `media-dispatch`.
Uzupełnia `RULE[user_global]` — nie zastępuje.

> Ostatnia aktualizacja: 2026-08-29 | Supervisor 01

---

## Cel workspace

`media-dispatch` to autonomiczne centrum zarządzania contentem.
System agentów AI który zbiera tematy, produkuje treści i dystrybuuje je
na wiele platform bez ręcznej pracy redakcyjnej.

**Platformy docelowe:** WordPress portale, YouTube, TikTok, Telegram.  
**Systemy produkcji:** VSE (Video SEO Engine), PressAI, Shorts Machine.

---

## Mapa workspace

| Workspace | Repo | Branch | Owner |
|---|---|---|---|
| media-dispatch | `media-dispatch` | `main` | gitomwtyczka |

---

## Callsigny

| Callsign | Rola |
|----------|------|
| `media-strateg` | Supervisor / Redaktor Naczelny |
| `media-dev-XX` | Implementacja workerów |
| `media-analyst` | Analiza, raportowanie |
| `media-deploy` | Deploy workerów na VPS |

---

## Architektura

### Warstwa 1 — Intelligence
- `feed-crawler-worker` — RSS monitoring
- `content-radar-worker` — Google Trends + social

### Warstwa 2 — Editorial
- `redaktor-naczelny` — meta-agent syntetyzujący wywiad

### Warstwa 3 — Production
- `vse-worker` — video → transkrypcja Whisper → SEO + shorty + draft WP
- `pressai-worker` — tekst/link/mail → artykuł

### Warstwa 4 — Distribution
- `youtube-worker`, `wp-publisher`, `tiktok-worker`, `telegram-worker`

---

## Infrastruktura VSE

| Element | Wartość |
|---------|--------|
| VPS | `ubuntu@147.224.162.100` |
| SSH key | `C:\Users\tomas2\.ssh\oracle-crimson.key` (pełna ścieżka Windows) |
| VSE URL publiczny | `https://vse.impresjapr.pl` |
| VSE port wewnętrzny | **8085** (NIE 8000!) |
| VSE containers | `vse-api`, `vse-web`, `vse-postgres` |
| Dashboard | `https://vse.impresjapr.pl/dashboard` |

> ⚠️ Szczegółowa wiedza operacyjna (auth, pułapki, wzorce kodu) →
> [`.agents/knowledge/vse-worker-constitution.md`](.agents/knowledge/vse-worker-constitution.md)

---

## Kanały YouTube obsługiwane

| Kanał | Konto | Playlista |
|-------|-------|-----------|
| Prawy TV | tobroz@gmail.com | — |
| Prawy Biblijny | tobroz@gmail.com | `PLw7UeigJuyWkUzzvhS1vZX0H251raaYa7` |

Oba kanały używają tego samego OAuth (to samo konto Google).
Konfiguracja kanałów w **bazie danych VSE** — nie w plikach YAML.

---

## Portale WordPress

| Portal | URL | portal_id w VSE |
|--------|-----|----------------|
| Prawy.pl | https://prawy.pl | `prawy` |

---

## Reguły implementacyjne

1. Każdy worker implementuje: `health_check()`, `process(task)`, `get_status()`
2. Stan per content item w `shared/state/`
3. Zadania przez task queue: `shared/tasks/queue.json`
4. Raporty do `.agents/reports/` + dual-write do `sonic-void/.agents/reports/inbox/`
5. Heartbeat na starcie sesji
6. Pliki projektowe — **wyłącznie GitHub MCP** (nie `write_to_file` na lokalnym klonie)

---

## Pre-flight checklist dla media-dev / media-deploy

Przed pierwszym `run_command` lub wywołaniem VSE API:

1. Przeczytaj `vse-worker-constitution.md` — zwłaszcza sekcję **Znane Pułapki**
2. Sprawdź czy masz działający JWT token (weryfikacja: `GET /v1/users/me`)
3. Token generuj przez `jose.jwt.encode()` wewnątrz `vse-api` — NIE przez `create_access_token()`
4. Dla skryptów z SQL lub złożonym escapingiem: `write_to_file` → `scp` → `ssh bash /tmp/skrypt.sh`
5. SCP — zawsze pełne ścieżki Windows (nie `~`)

---

*Inicjacja: media-dev-01 | 28.08.2026*  
*Rozbudowa: Supervisor 01 | sonic-void | 29.08.2026 — VSE infra, kanały, pre-flight*
