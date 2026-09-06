# Raport: Radar UI/UX Finalization & PressAI Hotfix
**Data:** 2026-09-06
**Callsign:** media-dev-30
**Status:** Zakończono z sukcesem ✅

## Wykonane kroki:
1. **Zadanie 1: Excel UX (Dropdowny i Nowe Kolumny)**
   - Stworzono skrypt `update_radar_ui.py` korzystający z API Google Sheets (metoda `batch_update`).
   - Wstawiono 2 nowe kolumny pomiędzy *Źródło* a *Tytuł SEO*. Nowy układ (A-H): Temat, Źródło, Link do źródła, Data opublikowania źródła, Tytuł SEO, Frazy kluczowe, Obrazek główny, Status.
   - Założono Data Validation (Dropdown) na całą kolumnę H (Status) ograniczając poprawne wartości do żądanej listy (*Nowa Propozycja, Publikuj w PressAI, Odrzucone, Opublikowane*).

2. **Zadanie 2: Refaktoryzacja `radar_sheets_sync.py`**
   - Poprawiono kod w celu dostosowania odczytu i parsowania indeksów do 8-kolumnowego układu (w sekcji `mode_fetch` oraz `process_row_publish`).
   - Usunięto niepoprawne parsowanie zdarzeń SSE i wymieniono na czyste odczytywanie JSON: `response.json().get('result', {}).get('generated_article', '')`.
   - Zmieniono w `get_radar_jwt()` autoryzację na zaciąganie tokenu ze zmiennej `.env` o nazwie `CONTENT_RADAR_JWT`.
   
3. **Wdrożenie na serwer:**
   - Zaktualizowany skrypt `radar_sheets_sync.py` został poprawnie przesłany i wdrożony na serwer produkcyjny Oracle (VPS) poleceniem `scp`.
   - Kod został wypchnięty do repozytorium `media-dispatch`.