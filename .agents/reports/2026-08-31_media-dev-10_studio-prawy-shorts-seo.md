# Raport: Optymalizacja SEO i harmonogram 8 Shorts Studio Prawy_PL

**Data:** 2026-08-31  
**Agent:** media-dev-10  
**Kanał docelowy:** Studio Prawy_PL (`UCoH2G9By4OX3kcLsc8lHgDw`)  
**Status bazowy:** `private` (wszystkie materiały)

---

## 1. Wykonane działania

1. **Autoryzacja i tokeny:**
   - Wygenerowano JWT do instancji VSE API.
   - Odświeżono token OAuth Google dla kanału `Studio Prawy_PL` (`UCoH2G9By4OX3kcLsc8lHgDw`) w oparciu o silnik `_build_credentials()`.
2. **Optymalizacja SEO 8 materiałów Shorts:**
   - Zastąpiono robocze nazwy plików (np. `Pakt_z_Niemcami_w_1939..._gotowy.mp4`) czytelnymi, chwytliwymi tytułami SEO (do 70 znaków).
   - Opracowano opisy zoptymalizowane pod algorytm Shorts: 1-2 zdaniowy hook, call-to-action (subskrypcja + link do prawy.pl) oraz precyzyjne hashtagi tematyczne.
3. **Aktualizacja przez YouTube Data API v3:**
   - Zaktualizowano snippet (tytuł, opis) dla każdego z 8 filmów.
   - **Bezpieczeństwo statusu:** Wszystkie wideo zachowały status `private`.
   - **Harmonogram (publishAt):** Dla 3 wybranych shortów ustawiono daty automatycznej publikacji. YouTube API pomyślnie zaakceptowało `publishAt`.

---

## 2. Tabela podsumowująca 8 Shorts

| YT ID | Tytuł SEO | Opis (pierwsze 80 znaków) | Status / Data zaplanowana |
|---|---|---|:---:|
| `FtQNSzHtQ0s` | **Pakt z Niemcami w 1939 roku? Szokująca prawda o planach Hitlera!** | Czy Polska mogła pójść na układ z III Rzeszą w 1939 roku? Poznaj kulisy dyplomac... | `private` → Zaplanowano: **2026-09-01 07:00** |
| `mw6A9CZ6DuM` | **Zdrada w Monachium 1938! Jak mocarstwa oddały Czechosłowację** | Konferencja w Monachium w 1938 roku to jedna z największych zdrad w historii dyp... | `private` (gotowy do emisji) |
| `ioObSLpRGc4` | **Kłamstwo Putina o II wojnie! Dlaczego ukrywają 1939 rok?** | Dla Rosji Putina II wojna światowa nie zaczęła się w 1939 roku. Dlaczego Kreml p... | `private` → Zaplanowano: **2026-09-01 12:00** |
| `mTyr64ygkJU` | **Czas na porządek w polskim prawie! Konieczna naprawa państwa** | W Polsce trzeba wreszcie uporządkować system prawny i ustrojowy. Czy obecny chao... | `private` (gotowy do emisji) |
| `8nbA6YSZAVQ` | **Kto naprawdę stoi za Akcją Demokracja? Finansowanie i wpływy NGO** | Akcja Demokracja i organizacje pozarządowe w Polsce — czy to autentyczny głos ob... | `private` (gotowy do emisji) |
| `slA15REfjpU` | **Konstytucja z 1997 roku to bubel prawny? Szokujące wady ustawy!** | Konstytucja z 1997 roku ma fundamentalne wady i braki, które paraliżują państwo... | `private` → Zaplanowano: **2026-09-01 18:00** |
| `9tjEXGE5sXg` | **Wyprowadzili 500 milionów złotych?! Skandal i kulisy afery!** | Ten projekt służył tylko jednemu: wyprowadzeniu 500 milionów złotych z publiczny... | `private` (gotowy do emisji) |
| `lX2vvs8E-AY` | **Brak własnego zdania w polityce? Złośliwy, ale celny komentarz!** | „Złośliwi mówili, że jak ktoś nie ma własnej inicjatywy...” — błyskotliwa i celn... | `private` (gotowy do emisji) |

---

## 3. Wynik harmonogramowania (publishAt)

- `FtQNSzHtQ0s` (Pakt 1939): **Zaakceptowano** (`2026-09-01T07:00:00+02:00`)
- `ioObSLpRGc4` (Kłamstwo Putina): **Zaakceptowano** (`2026-09-01T12:00:00+02:00`)
- `slA15REfjpU` (Konstytucja 1997): **Zaakceptowano** (`2026-09-01T18:00:00+02:00`)

Ręczne ustawianie dat w YouTube Studio dla tej trójki **nie jest wymagane** — YouTube sam opublikuje filmy o wyznaczonych godzinach.
Pozostałe 5 filmów pozostaje w stanie `private` i może zostać zaplanowane w kolejnych slotach emisyjnych.
