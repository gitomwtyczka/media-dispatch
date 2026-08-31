# Raport: Pipeline VSE Mosiński 2, Weryfikacja Śliwki i Render Shortów

**Data:** 2026-08-31  
**Autor:** `media-dev-03`  
**Status:** ✅ Sukces (Zadania A, B, D, E zakończone | Zadanie C zidentyfikowane i gotowe)

---

## 1. Podsumowanie zadań

| Zadanie | Przedmiot | Status | Szczegóły / Wynik |
|---|---|---|---|
| **A** | Śliwka (`yQ-Q_YrleLE`) | ℹ️ Zbadany | W bazie VSE (`transcript_jobs`) istnieją 2 wpisy ze statusem `done`. Pole `wp_id: 0` (artykuł nie został jeszcze wstrzyknięty do WordPressa). |
| **B** | Mosiński 2 (`zYcq-57Y0ts`) | ✅ Sukces | Wygenerowano analizę Claude (`full_analysis`), utworzono wpis w WordPress `#125367` (status `future` na `2026-09-02T10:00:00+02:00`), zaktualizowano YouTube do `public` z tytułem i opisem SEO. |
| **C** | Płużański Rulewski | 🟡 Gotowy do startu | Znaleziono na YT Studio Prawy_PL: `EnclbKLEDAA` (tytuł `Płużanski Rulewski.mp4`, napisy ASR `serving`). Plik lokalny: `C:\Users\tomas2\Videos\Prawy\Płużanski Rulewski.mp4`. Czeka na potwierdzenie. |
| **D** | Shorts candidates | ✅ Sukces | Wygenerowano po 10 propozycji (5 emocjonalnych + 5 profesjonalnych) przez Claude dla Mosińskiego 1 i Mosińskiego 2. Zapisano do `/home/ubuntu/video-seo-engine/batch/shorts_candidates_2026-08-31.json`. |
| **E** | Local Runner & Shorts Render | ✅ Sukces | Uruchomiono `VSELocalRunner` na PC. Zgłoszono 10 render jobs z explicit `local_path`. Runner wyrenderował 10 klipów do `C:\VSE\Shorts\`. |

---

## 2. Szczegóły publikacji Mosiński 2 (`zYcq-57Y0ts`)

- **YouTube URL:** https://www.youtube.com/watch?v=zYcq-57Y0ts
- **Tytuł YouTube:** *Mosiński: Solidarność zdradzona – co zostało z idei roku 80?*
- **Status YouTube:** `public`
- **WP Post ID:** `125367`
- **WP Post URL:** https://prawy.pl/testament-solidarnosci-czy-idealy-z-1980-roku-przetrwaly-do-dzis/
- **Status WP:** `future` (zaplanowana publikacja: `2026-09-02 10:00:00`)
- **RankMath SEO:** `true`

---

## 3. Wyrenderowane Shorty (`C:\VSE\Shorts`)

### Mosiński 1 (`s6aGNXdtKpA`) -> `C:\VSE\Shorts\Płużanski Mosinski 1_2026-08-31\`
1. `Niech_zstapi_Duch_Twoj_i_odnowi_oblicze_ziemi_4m47s-5m34s_raw.mp4` (+ srt, submachine.srt)
2. `Posłanie_do_ludzi_pracy_Europy_Wschodniej_Pol_8m30s-9m18s_raw.mp4` (+ srt, submachine.srt)
3. `Posłanie_do_ludzi_pracy_Europy_Wschodniej_wst_9m01s-9m42s_raw.mp4` (+ srt, submachine.srt)
4. `robotnikow_robotnikow_ale_ale_przeciez_były_t_3m44s-4m30s_raw.mp4` (+ srt, submachine.srt)
5. `Zaskoczyła_mnie_szybkosc_powstania_Solidarnos_2m25s-3m12s_raw.mp4` (+ srt, submachine.srt)

### Mosiński 2 (`zYcq-57Y0ts`) -> `C:\VSE\Shorts\Płużanski Mosinski 2_2026-08-31\`
1. `Gdyby_dzisiaj_Donald_Tusk_był_działaczem_Soli_16m08s-16m56s_raw.mp4` (+ srt, submachine.srt)
2. `Gdzie_jest_Donald_Tusk_15_sierpnia_w_rocznice_8m40s-9m25s_raw.mp4` (+ srt, submachine.srt)
3. `Okragły_Stoł_na_tamten_czas_wydawał_sie_przed_4m33s-5m33s_raw.mp4` (+ srt, submachine.srt)
4. `Wrocił_Tusk_wrociły_afery_wrociło_bezrobocie_10m30s-11m18s_raw.mp4` (+ srt, submachine.srt)
5. `Zaginał_oryginał_21_postulatow_gdanskich_Nie_0m50s-1m28s_raw.mp4` (+ srt, submachine.srt)
