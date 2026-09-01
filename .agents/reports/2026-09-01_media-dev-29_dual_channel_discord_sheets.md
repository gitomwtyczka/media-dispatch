# Raport: Dual-channel Discord + Kolory Priorytetowe w Sheets

**Callsign:** media-dev-29  
**Data:** 01.09.2026  
**Workspace:** media-dispatch  
**Status:** ✅ Gotowe  

---

## 1. Zakres prac i wykonane zadania

### ZADANIE 1: Dual-channel Discord w `WorkerBase`
- Zaktualizowano metodę `notify_discord()` w `agents/base/worker_base.py`:
  - Obsługa dwóch webhooków: `general_url` (`DISCORD_WEBHOOK_KURIER365`) oraz `priority_url` (`DISCORD_WEBHOOK_PRIORITY`).
  - Rozróżnienie kandydatów:
    - Gmail (`is_gmail = candidate.source.startswith('gmail:')`): złoty kolor embeda `0xFFD700`, ikona `📧`, nagłówek `🔔 **PRIORYTET — współpracownik** | {sender}`.
    - P0 (`priority >= 8`): czerwony kolor `0xdc3545`, nagłówek `🔴 **PRIORYTET P0** | {portal}`.
    - P1 (`priority >= 6`): pomarańczowy `0xfd7e14`.
    - P2 (`priority >= 4`): żółty `0xffc107`.
    - Default: niebieski `0x1a73e8`.
  - Routing: każdy kandydat trafia na kanał ogólny, a kandydaci P0 lub Gmail dodatkowo na kanał priorytetowy.
- **Commit:** `ae1546f6e1d439c4550ec74ace9730a3a0f16c17`

### ZADANIE 2: Konfiguracja VPS (`.env`)
- Zdefiniowano zmienną `DISCORD_WEBHOOK_PRIORITY=PLACEHOLDER_PRIORITY_URL` w `.env` (`/home/ubuntu/media-dispatch/.env`).
- Dołączono obsługę w `agents/kurier365-worker/worker.py` (wyświetlanie statusu w `--health`).

### ZADANIE 3: Google Sheets Conditional Formatting dla zakładki "Kandydaci"
- Arkusz: `1HMuODAIOG8e_9VH-HitdL_TwBRwgFZ0vnSKAW7Wmyig` (GID `1842692147`, zakres `A2:R50`).
- Przygotowano i zcommitowano skrypt automatyzujący `agents/sheets-sync-worker/apply_kandydaci_formatting.py`.
- Reguły formatowania warunkowego:
  1. **Gmail:** `=REGEXMATCH(LOWER($C2), "gmail:")` -> tło złote `{red: 1.0, green: 0.843, blue: 0.0}` (#FFD700).
  2. **P0:** `=OR($F2="P0", REGEXMATCH(TO_TEXT($F2), "(?i)P0"))` -> tło czerwone `{red: 0.957, green: 0.6, blue: 0.6}`.
  3. **P1:** `=OR($F2="P1", REGEXMATCH(TO_TEXT($F2), "(?i)P1"))` -> tło pomarańczowe `{red: 0.992, green: 0.749, blue: 0.502}`.
  4. **P2:** `=OR($F2="P2", REGEXMATCH(TO_TEXT($F2), "(?i)P2"))` -> tło żółte `{red: 1.0, green: 0.949, blue: 0.6}`.
  5. **P3:** `=OR($F2="P3", REGEXMATCH(TO_TEXT($F2), "(?i)P3"))` -> tło szare `{red: 0.85, green: 0.85, blue: 0.85}`.
- **Commit:** `85359537104f7d746a270826b3c55d80729a6306`

### ZADANIE 4: Dokumentacja w `AGENTS.md`
- Dodano sekcję o architekturze dwóch kanałów Discord dla kurier365:
  - `#editorial-kurier365` — wszystkie kandydaci (`DISCORD_WEBHOOK_KURIER365`)
  - `#editorial-priority` — tylko P0 i współpracownicy Gmail (`DISCORD_WEBHOOK_PRIORITY`)
- **Commit:** `505a054ef0c550a697e7fcd655cea704da38735f`

---

## 2. Podsumowanie commitów

1. `ae1546f6e1d439c4550ec74ace9730a3a0f16c17` — `feat: dual-channel Discord notification in WorkerBase [media-dev-29]`
2. `505a054ef0c550a697e7fcd655cea704da38735f` — `docs: update AGENTS.md with dual-channel Discord architecture [media-dev-29]`
3. `85359537104f7d746a270826b3c55d80729a6306` — `feat: add apply_kandydaci_formatting.py for Google Sheets conditional formatting [media-dev-29]`
4. `c4544b77736b332063362be1751599b7773f13ec` — `feat: update kurier365 worker CLI with DISCORD_WEBHOOK_PRIORITY support [media-dev-29]`
