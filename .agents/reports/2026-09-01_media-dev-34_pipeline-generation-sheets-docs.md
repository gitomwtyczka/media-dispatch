# Raport: Poprawki pipeline generowania, Google Sheets i dokumentacji publikacji

> **Autor:** `[media-dev-34 | media-dispatch 01.09.2026]`  
> **Status:** ✅ Zrealizowane  
> **Repozytorium:** `media-dispatch`  
> **Powiązane pliki:** `agents/kurier365-worker/worker.py`, `docs/publication-flow.md`, Google Sheets `1HMuODAIOG8e_9VH-HitdL_TwBRwgFZ0vnSKAW7Wmyig`

---

## 1. Cel zadania

Realizacja trzech zadań usprawniających pipeline produkcyjno-publikacyjny Kurier365 / BiznesCiti:
1. Naprawa promptu i parametrów generowania w `kurier365-worker` (POST `/api/editor/generate`), routing portali, zapis do historii PressAI bez natychmiastowej publikacji (z wyjątkiem wybranych nadawców ze zdjęciami) oraz aktualizacja statusów w Google Sheets.
2. Rozszerzenie zakładki *Kandydaci* w arkuszu Google Sheets o kolumny S i T (`Prompt obraz 1`, `Prompt obraz 2`) o szerokości 300px z właściwym formatowaniem nagłówka i notatką.
3. Utworzenie dokumentacji `docs/publication-flow.md` opisującej pełny standardowy flow oraz wyjątki.

---

## 2. Zrealizowane prace

### Zadanie 1: kurier365-worker (`agents/kurier365-worker/worker.py`)
- **Prompt generowania:** Zaktualizowano `custom_instructions` (wymóg min. 600 słów / optymalnie 800-1000, tytuł SEO H1 z frazą, język polski, Google Discover, FAQ min. 3 pytania, cross-link BiznesCiti) oraz ustawiono `generate_faq: True` i `min_words: 600`.
- **Kategoryzacja portalu:** Zaimplementowano funkcję `_get_target_portal(candidate)` kierującą materiały (Gmail współpracownicy, nauka, geostrategia/obronność -> `Kurier365`; biznes/gospodarka/finanse/ekonomia -> `BiznesCiti`).
- **Flow publikacji & historia PressAI:**
  - Po wygenerowaniu artykuł jest zapisywany w historii PressAI (POST `/api/articles/`).
  - Standardowo artykuł NIE jest publikowany bezpośrednio do WordPressa (czeka na dodanie grafik w UI PressAI).
  - **Wyjątek:** Nadawcy posiadający własne materiały graficzne (`zabka`, `juchniewicz`, `rudzinski`) są automatycznie kierowani do publikacji jako draft WP (POST `/api/publisher/publish`).
- **Aktualizacja Sheets:** Zaimplementowano `update_candidate_in_sheets`, która ustawia wiersz kandydata na Status = `'w produkcji'` oraz uzupełnia URL draftu WP (jeśli wystąpił auto-draft).
- **Commit SHA:** `d6eb8ea5a75383447c95831493106e0e9422dbdc`

### Zadanie 2: Kolumny promptów obrazów w Google Sheets
- Wykonano operację przez Google Sheets API / gspread z użyciem klucza Service Account `/home/ubuntu/otwock-data/muzeum/muzeum-drive-sa.json` na Oracle VPS.
- Do zakładki `Kandydaci` dodano kolumny:
  - **Kolumna S (19):** `Prompt obraz 1` (szerokość 300px)
  - **Kolumna T (20):** `Prompt obraz 2` (szerokość 300px)
- Sformatowano nagłówki zgodnie ze stylem arkusza (ciemnozielone tło `#1c5e21`, biały pogrubiony tekst, wyśrodkowanie).
- Dodano notatkę w nagłówkach: `Prompt do generatora obrazow AI (Midjourney/DALL-E/Flux)`.

### Zadanie 3: Dokumentacja Publication Flow (`docs/publication-flow.md`)
- Utworzono dokumentację `docs/publication-flow.md` opisującą standardowy flow publikacji, wyjątki z auto-draftem, kolumny na prompty obrazów oraz routing tematyczny portali.
- **Commit SHA:** `3d66c80e97f225ddac44ece390d7c7aa859399f5`

---

## 3. Podsumowanie commitów

| Plik | Akcja | Commit SHA |
|------|-------|------------|
| `docs/publication-flow.md` | Dodanie specyfikacji flow publikacji | `3d66c80e97f225ddac44ece390d7c7aa859399f5` |
| `agents/kurier365-worker/worker.py` | Aktualizacja promptu, routingu, PressAI i Sheets | `d6eb8ea5a75383447c95831493106e0e9422dbdc` |
