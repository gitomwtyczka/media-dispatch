# AGENTS.md — media-dispatch

Reguły specyficzne dla workspace `media-dispatch`.
Uzupełnia `RULE[user_global]` — nie zastępuje.

> Ostatnia aktualizacja: 2026-08-31 | media-dev-06

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

## ⛔ REGUŁA PUBLIKOWANIA — BEZWZGLĘDNA

Żaden materiał NIE może zostać opublikowany (status: publish/public/future) bez:
1. Jawnego zatwierdzenia w arkuszu Google Sheets (kolumna Status = 'Zatwierdź'), LUB
2. Jawnego komunikatu od użytkownika z nazwą materiału i datą publikacji.

DOMYŚLNY STATUS zawsze:
- WordPress: `draft`
- YouTube: `unlisted`

WYJĄTEK: tylko gdy użytkownik poda explicite "opublikuj", "publish", "live" lub konkretną datę publikacji przy zleceniu.

Naruszenie tej reguły = błąd krytyczny wymagający natychmiastowego rewertu.

---

## Short Machine
- Short Machine = część VSE, będzie niezależnym modułem z własnym API
- Mieszka w video-seo-engine, rozwija się jako osobny serwis
- Integracja przez API endpoint (do ustalenia gdy API będzie gotowe)
- Shorty na YouTube: upload ręczny przez użytkownika z Premiere Pro
- TikTok: upload ręczny z Premiere Pro, opisy przez Short Machine (roadmap)

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

## DISPATCH PROTOCOL — zasady przekazywania wiedzy

> Dodane: 2026-08-30 | media-strateg — lekcja z sesji backlog 28-29.08

### Zasada naczelna: wiedza w dispatchu, nie odkrywana przez workera

Worker NIE szuka tokenów, dostępów ani procedur na własną rękę.
Supervisor dostarcza gotowe narzędzia i wiedzę — worker wykonuje.

### Hierarchia źródeł wiedzy (kiedy Supervisor czegoś nie wie)

Jeśli brakuje informacji do dispatchu — szukaj w tej kolejności:

```
1. .agents/knowledge/         ← konstytucje workerów, recepty, pułapki
2. agents/*/scripts/          ← gotowe skrypty z poprzednich sesji (WZORZEC!)
3. .agents/reports/           ← raporty z poprzednich sesji
4. .agents/tasks/CURRENT_BRIEF.md ← ostatni znany stan projektu
5. heartbeat.json             ← co zrobiła poprzednia sesja
```

NIE zaczynaj od zera gdy istnieje wcześniejszy skrypt robiący to samo.

### Co musi zawierać dobry dispatch

```
## KONTEKST (kopiuj z wiedzy, nie każ workerowi szukać)
- Gotowy skrypt lub referencja do istniejącego
- Znane komendy (SSH pattern, API endpoints)
- Parametry specyficzne dla zadania (video_id, daty, portal_id)
- Lokalizacja plików wejściowych

## ZADANIE (precyzyjne, bez eksploracji)
- Jedna główna komenda lub sekwencja kroków
- Oczekiwany output
- Co zrobić przy błędzie

## ⚠️ ZNANE PUŁAPKI (z konstytucji)
- Kopiuj bezpośrednio z vse-worker-constitution.md sekcja 7
```

### Self-contained scripts — wzorzec

Kiedy worker musi wykonać pipeline:
- Skrypt pobiera własne tokeny na starcie (subprocess SSH dla JWT)
- Wszystkie parametry hardcoded w CONFIG sekcji
- Worker dostaje jedną komendę: `python skrypt.py`
- Wzorzec: `agents/vse-worker/scripts/biblia_backlog_pipeline.py`

### Odkładanie wiedzy przez workera

Worker po zakończeniu zadania POWINIEN zaktualizować:
- `.agents/knowledge/` — jeśli odkrył nową pułapkę lub wzorzec
- `.agents/reports/` — raport z wynikami (dual-write do sonic-void)
- Istniejący skrypt w `agents/*/scripts/` — jeśli naprawił bug lub dodał feature

Worker MOŻE odkładać tymczasową wiedzę w scratch swojego workspace
(np. zapisane tokeny do ponownego użycia w tej samej sesji).

### Anty-wzorzec (czego NIE robić)

❌ Dispatch: "pobierz JWT token" → worker szuka jak to zrobić  
✅ Dispatch: "uruchom `python biblia_backlog_pipeline.py` — skrypt sam pobiera token przez SSH"

❌ Dispatch: "sprawdź konfigurację YT w VSE"  
✅ Dispatch: "kanał Prawy Biblijny, konto tobroz@gmail.com, playlista PLw7UeigJuyWkUzzvhS1vZX0H251raaYa7"

❌ Worker odkrywa strukturę API metodą prób i błędów  
✅ Worker dostaje referencję do `vse-worker-constitution.md sekcja 3`

---

*Inicjacja: media-dev-01 | 28.08.2026*  
*Rozbudowa: Supervisor 01 | sonic-void | 29.08.2026 — VSE infra, kanały, pre-flight*  
*Rozbudowa: media-strateg | 30.08.2026 — Dispatch Protocol, self-contained scripts, hierarchia wiedzy*  
*Rozbudowa: media-dev-06 | 31.08.2026 — reguła publikowania bezwzględna, Short Machine*
