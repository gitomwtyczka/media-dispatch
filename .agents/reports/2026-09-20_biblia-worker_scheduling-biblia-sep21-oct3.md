# Raport sesji: biblia-worker | 20.09.2026

**Callsign:** biblia-worker  
**Data:** 2026-09-20  
**Status:** done ✅

---

## Wykonane zadania

### 1. Scheduling 13 filmów biblijnych (Sep 21 – Oct 3 2026)

Wszystkie 13 filmów zaplanowanych na YouTube (privacyStatus=private + publishAt) i WordPress (post_status=future).

| Data | Czytanie | YouTube ID | WP Post ID |
|------|----------|------------|------------|
| 21.09.2026 00:00 CEST | Łk 8,11-16 | IQ08oawsqZY | 126709 |
| 22.09.2026 00:00 CEST | Łk 8,19-21 | x_NXbSEgQrE | 126714 |
| 23.09.2026 00:00 CEST | Łk 9,1-6 | DmUKkMF8h8I | 126719 |
| 24.09.2026 00:00 CEST | Łk 9,7-9 | O8h28o-hl0Y | 126724 |
| 25.09.2026 00:00 CEST | Łk 9,18-22 | zjwkbntfTfw | 126729 |
| 26.09.2026 00:00 CEST | Łk 9,43b-45 | Yy9QFIxq-V4 | 126734 |
| 27.09.2026 00:00 CEST | Mt 21,28-32 | BiHACQyOvJE | 126739 |
| 28.09.2026 00:00 CEST | Łk 9,46-50 | -7QysZhJ7Wg | 126744 |
| 29.09.2026 00:00 CEST | Łk 9,51-56 | xrnfUH3t95k | 126749 |
| 30.09.2026 00:00 CEST | Łk 9,57-62 | dbTJHhqx7rY | 126754 |
| 01.10.2026 00:00 CEST | Łk 10,1-12 | bvrLRDoOELs | 126759 |
| 02.10.2026 00:00 CEST | Łk 10,13-16 | VA5D09x7r2c | 126764 |
| 03.10.2026 00:00 CEST | Łk 10,17-24 | N06YV7dzkMU | 126769 |

**Uwaga:** 6 filmów Sep 21-26 było błędnie opisanych na YouTube (etykiety lk 6 zamiast łk 8/9) — treść poprawna, opisy zostały wygenerowane przez VSE na podstawie rzeczywistej transkrypcji.

**Transcript fallback:** Nie był potrzebny — wszystkie 13 filmów miało dostępny auto-transkrypt YT.

### 2. Usunięcie duplikatów YouTube
- `HxlTUQn0hxc` — DELETED (duplikat Łk 6,20-26 / Sep 9)
- `rMwmrSBHxOE` — DELETED (duplikat Łk 10,17-24 / Oct 3)

### 3. Aktualizacja konstytucji VSE
- Dodana sekcja 16: ścieżki lokalne nagrań + procedura MP3 fallback
- Commit: f7e56d2878babf600922b5e3ec06f16d7d6f4f7f
- AME log path: C:\Users\tomas2\Documents\Adobe\Adobe Media Encoder\26.0\AMEEncodingLog.txt

### 4. Nowy skrypt w repozytorium
- `agents/vse-worker/scripts/biblia_schedule_pipeline.py` — commit 31e93cb
- Self-contained pipeline: YT captions → VSE generate → WP future → YT scheduled → playlista

---

## Klucze wiedzy zdobytej

1. Filmy biblijne mogą być błędnie opisane na YT — VSE regeneruje opisy z transkrypcji (treść zawsze prawdziwa)
2. Auto-transkrypt YT dostępny nawet dla filmów wgranych tego samego dnia
3. Duplikaty YT usuwa konto `Prawy TV` (nie `Tomasz Brzozowski` — brak uprawnień)
4. AME log (UTF-16LE) pozwala mapować YT ID → ścieżka lokalna MP4

---

*biblia-worker | media-dispatch | 20.09.2026 18:26*
