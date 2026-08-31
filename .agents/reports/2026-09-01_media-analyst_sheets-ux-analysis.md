# Raport Analityczny: Analiza UX i Architektury Google Sheets 'Nagrania prawy'

> **Autor:** `media-analyst` (`[media-analyst-sheets]`)  
> **Data:** 01.09.2026  
> **Workspace:** `media-dispatch`  
> **Dokumentacja pełna:** [`docs/sheets-ux-analysis.md`](../../docs/sheets-ux-analysis.md)  
> **Status:** Raport kompletny  

---

## 1. Podsumowanie zadania
Przeprowadzono szczegółowy audyt Google Sheets 'Nagrania prawy' (ID: `1zqwvS784EaZh1EJIcXk1DliAau1r4X15ENFJjloDSaM`, GID: `809929940`) pod kątem workflow redakcyjnego, integracji z VSE, Short Machine, WordPress (prawy.pl) oraz kanałami YouTube/TikTok.

Pełny raport został zapisany w repozytorium: [`docs/sheets-ux-analysis.md`](../../docs/sheets-ux-analysis.md).

---

## 2. TOP 5 Rekomendacji Architektonicznych

1. **Dedykowana zakładka `📱 Shorts & Reels` z relacją do filmu bazowego (`Parent YouTube ID`)**: Pełna widoczność metadanych Short Machine (hooki max 45 zn, hashtagi bez #Shorts, pinned comments) i harmonogramu slotów (`07:00`, `12:00`, `18:00`, `21:00 CEST`).
2. **Rozbicie jednolitego statusu na 4 niezależne wymiary**: Wprowadzenie osobnych statusów dla backendu (`Status VSE`), redakcji (`Status Review / Human Gate`), portalu (`Status WP`) oraz wideo (`Status YouTube`).
3. **Wprowadzenie bramki Human-in-the-Loop**: Dodanie pól `Zatwierdził(a)`, `Status Akceptacji` (*Do akceptacji*, *Zatwierdzony*, *Do poprawy*, *HOLD*) i `Uwagi redakcyjne`, co eliminuje bałagan w polu `Notatki`.
4. **Rozdzielenie cyklu produkcyjnego na datę nagrania vs datę emisji**: Dodanie kolumn `Data nagrania w studio`, `Data emisji` oraz `Gość / Rozmówca` i `Prowadzący`, co umożliwia pre-produkcję i planowanie ramówki.
5. **Zamknięcie pętli analitycznej (Feedback Loop)**: Zautomatyzowanie nocnego pobierania statystyk (wyświetlenia 24h/7d, APV retencji shortów, CTR miniatury, odsłony WP) do zakładki analitycznej.

---

## 3. Quick Wins (do wdrożenia dzisiaj)

1. **Walidacja danych (Dropdowny) + Warunkowe kolorowanie (Conditional Formatting)** dla kolumn `Status` i `Short Machine` (zielony=opublikowany/TAK, żółty=w toku/draft, czerwony=hold/wstrzymany/NIE, niebieski=do akceptacji).
2. **Dodanie kolumn `Gość / Rozmówca`, `Prowadzący` oraz `Kategoria WP`** do skryptu `update_editorial.py` i wierszy 10–14 w arkuszu.
3. **Poprawa ergonomii UI**: Zamiana surowych linków tekstowych na aktywne formuły `=HYPERLINK(url; "📺 YouTube")` i `=HYPERLINK(url; "📝 WP Artykuł")` oraz włączenie zawijania wierszy (Wrap text).

---

*[media-analyst-sheets | media-dispatch 01.09.2026] — raport kompletny*
