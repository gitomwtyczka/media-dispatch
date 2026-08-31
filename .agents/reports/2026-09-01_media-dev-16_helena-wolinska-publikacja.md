# Raport wdrożeniowy: Publikacja materiału Helena Wolińska & Shorts Pipeline

**Autor:** `media-dev-16`  
**Data:** 01.09.2026 00:45 CEST  
**Workspace:** `media-dispatch`  
**Temat:** Publikacja filmu Helena Wolińska na prawy.pl i YouTube + Shorts pipeline  

---

## 1. Status Publikacji WordPress (prawy.pl)
- **Status:** ✅ Opublikowano (`publish`)
- **WP Post ID:** `125377`
- **Tytuł:** `Helena Wolińska: bestia w mundurze i morderca gen. Nila`
- **URL:** https://prawy.pl/helena-wolinska-bestia-w-mundurze-i-morderca-gen-nila/
- **SEO / Schema:** RankMath OK (`rankmath_ok: true`), pełna struktura VideoObject + FAQ + powiązane źródła

## 2. Status YouTube
- **YouTube ID:** `cDMAe_wx_AU`
- **Kanał:** `Studio Prawy_PL` (`UCoH2G9By4OX3kcLsc8lHgDw`)
- **Tytuł:** `Helena Wolińska: bestia w mundurze i morderca gen. Nila`
- **Privacy Status:** ✅ `public` (zmieniono z `unlisted`)

## 3. Shorts Pipeline

### 3a. Renderowanie Shorts (`/v1/shorts/render`)
Plik lokalny źródłowy: `C:\Users\tomas2\Videos\Prawy\Klimczak Płużanski Wolinska.mp4`

| # | Zakres czasowy | Score | Job ID renderera | Status |
|---|---|---|---|---|
| 1 | 606.0s – 660.5s (54.5s) | 0.92 | `37ee17f4-7221-4de4-a169-21a1da86b166` | `pending` |
| 2 | 145.0s – 192.5s (47.5s) | 0.88 | `b7dd8878-9e37-4af4-8b96-b957d8f07b33` | `pending` |
| 3 | 630.0s – 682.5s (52.5s) | 0.86 | `dc0f3616-6dc3-4c17-a68b-c8177e2baabf` | `pending` |
| 4 | 2628.0s – 2682.5s (54.5s) | 0.84 | `57168d80-cbb2-4385-aa01-fdbefd1086a9` | `pending` |

### 3b. Metadane Short Machine (`/v1/shorts/describe`)
Wszystkie opisy wygenerowane zgodnie ze standardami (tytuł <= 45 zn, bez #Shorts w tagach, bez linków w opisie, angażujący pinned comment).

1. **Short #1 (606.0s - 660.5s):**
   - **Tytuł:** `Bestia w mundurze - dlaczego ją wybielają?` (42 zn)
   - **Opis:** `Dlaczego postać nazywana "bestią w mundurze" jest dziś wybielana? Rozmowa o kontrowersjach wokół stalinowskiej zbrodniarki i książki 'Stygmat'.`
   - **Hashtagi:** `#HistoriaPolski #MuzeumPolin #KontrowersjeHistoryczne #Stygmat`
   - **Przypięty komentarz:** `🤔 Czy można wybielić postać zwaną "bestią w mundurze"? Jakie jest Wasze zdanie na temat przepisywania historii? Całą rozmowę znajdziesz w powiązanym filmie poniżej! 👇`

2. **Short #2 (145.0s - 192.5s):**
   - **Tytuł:** `Żydokomuna w Wojsku Polskim? Szokujące fakty` (44 zn)
   - **Opis:** `Indoktrynacja komunistyczna w Wojsku Polskim wyzwalającym Polskę ze wschodu. Kim byli oficerowie polityczni i jak kształtowali nową rzeczywistość PRL?`
   - **Hashtagi:** `#HistoriaPolski #Komunizm #WojskoPolskie #Żydokomuna`
   - **Przypięty komentarz:** `🤔 Czy znaliście prawdziwą historię indoktrynacji komunistycznej w Wojsku Polskim? A może macie własne źródła na ten temat? Całą rozmowę znajdziesz w powiązanym filmie poniżej! 👇`

3. **Short #3 (630.0s - 682.5s):**
   - **Tytuł:** `Dlaczego bojkotuję Muzeum Polin? 🚫` (34 zn)
   - **Opis:** `Dlaczego w Muzeum Polin odbywa się rozmowa o książce Stygmat? Czemu ktoś publicznie zadeklarował bojkot tej instytucji i jakie ma do tego powody?`
   - **Hashtagi:** `#MuzeumPolin #Stygmat #HistoriaPolski #KontrowersyjnaRozmowa`
   - **Przypięty komentarz:** `🤔 Czy w Polsce powinno najpierw powstać Muzeum Historii Polski, czy Muzeum Historii Żydów Polskich? Dlaczego taka kolejność budzi emocje? Całą rozmowę znajdziesz w powiązanym filmie poniżej! 👇`

4. **Short #4 (2628.0s - 2682.5s):**
   - **Tytuł:** `Wolińska: Żydówka unikająca ekstradycji` (39 zn)
   - **Opis:** `Helena Wolińska odrzuciła ekstradycję do Polski, oskarżając kraj o antysemityzm. Brytyjski paszport i azyl polityczny – jak uniknęła odpowiedzialności?`
   - **Hashtagi:** `#HelenaWolińska #HistoriaPRL #Ekstradycja #WielkaBrytania #PolitykaPamięci`
   - **Przypięty komentarz:** `⚖️ Czy odwołanie się do tożsamości może usprawiedliwiać unikanie odpowiedzialności? Podziel się swoją opinią! Całą rozmowę na temat Heleny Wolińskiej i kontekstu historycznego znajdziesz w powiązanym filmie poniżej 👇`

---

## 4. Wnioski i podsumowanie
- Proces wstrzyknięcia do WordPress i aktualizacji metadanych YouTube przebiegł w 100% poprawnie.
- W bazie VSE `transcript_jobs` zaktualizowano rekord o `wp_id=125377` oraz link do posta.
- 4 shorty zostały przekazane do kolejki renderera, a ich metadane SEO są gotowe do publikacji po zakończeniu renderingu.
