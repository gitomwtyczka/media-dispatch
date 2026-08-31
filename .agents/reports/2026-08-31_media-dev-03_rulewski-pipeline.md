# Raport: Pełny Pipeline VSE — Płużański Rulewski (EnclbKLEDAA)

**Data:** 2026-08-31  
**Autor:** `media-dev-03`  
**Status:** ✅ Sukces (WP Draft + YT Unlisted + Shorts Render)

---

## 1. Szczegóły publikacji

| Element | Wartość |
|---------|---------|
| **YouTube ID** | `EnclbKLEDAA` |
| **YouTube URL** | https://www.youtube.com/watch?v=EnclbKLEDAA |
| **Tytuł YouTube** | *Rulewski vs Michałowski: Kłótnia o Solidarność i jej spadek* |
| **Tytuł SEO** | *Dziedzictwo Solidarności: co zostało z etosu? \| Prawy TV* |
| **Tytuł WP** | *Dziedzictwo Solidarności: Rulewski i Michałowski o etocie ruchu dziś* |
| **Portal** | prawy.pl (`2b047d7d-15a1-4d2f-8463-f89c2275bb73`) |
| **WP Post ID** | `125372` |
| **WP Post URL** | https://prawy.pl/?p=125372 |
| **Status wpisu WP** | `draft` (zgodnie z wytycznymi — data do decyzji) |
| **Status YouTube** | `unlisted` (zaktualizowano tytuł, opis SEO z rozdziałami, tagami i linkiem WP) |
| **Plik lokalny** | `C:\Users\tomas2\Videos\Prawy\Płużanski Rulewski.mp4` |

---

## 2. Przebieg operacji

1. **Generowanie VSE (`POST /v1/generate`):**
   - Parametry: `publication_type=full_analysis`, `portal_id=2b047d7d-15a1-4d2f-8463-f89c2275bb73`, `llm_provider=claude`, `lang=pl`.
   - Wynik: 200 OK — wygenerowano pełny artykuł SEO, strukturę rozdziałów i VideoObject schema.
2. **Wstrzyknięcie do WordPress (`POST /v1/inject`):**
   - Utworzono post WP #125372 na prawy.pl ze statusem `draft`.
   - RankMath SEO: `true`.
3. **Aktualizacja YouTube:**
   - Zaktualizowano tytuł SEO, opis z rozdziałami i linkiem do szkicu, zachowano status `unlisted`.
4. **Shorts Candidates & Render (`POST /v1/shorts/candidates` & `/v1/shorts/render`):**
   - Wygenerowano 10 propozycji przez model Claude.
   - Zgłoszono top 5 fragmentów z jawnym parametrem `local_path="C:\Users\tomas2\Videos\Prawy\Płużanski Rulewski.mp4"`.
   - Local runner odebrał zadania i przetwarza wycinki do katalogu `C:\VSE\Shorts\Płużanski Rulewski_2026-08-31\`.

---

## 3. Zgłoszone Shorty Rulewski (Top 5)

1. `Job ID: d8b393d4-9a49-4a17-96ed-720fa46c92c2` [1017.0s - 1069.5s]
2. `Job ID: 4c32874a-41c3-4ac3-ac5b-0f2fbd0371dd` [405.0s - 450.5s]
3. `Job ID: 9d5b6dd6-fef2-40a8-a207-52209d58c885` [2458.0s - 2521.5s]
4. `Job ID: f2537f6a-2198-43cb-af99-bb48ae4aa38d` [1587.0s - 1641.5s]
5. `Job ID: fb75d832-f207-4248-8055-f242a6d0680c` [750.0s - 796.5s]
