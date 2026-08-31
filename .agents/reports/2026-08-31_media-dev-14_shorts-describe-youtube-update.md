# Raport z wdrożenia opisu i aktualizacji YouTube Shorts — media-dev-14

**Data:** 2026-08-31 23:31  
**Autor:** `media-dev-14`  
**Status:** ✅ Sukces (8/8 zaktualizowanych shortów)

---

## 1. Cel zadania
- Pobranie specyfikacji i wymagań endpointa `POST /v1/shorts/describe` (VSE Short Machine).
- Zidentyfikowanie źródłowych `source_youtube_id` oraz timestampów (`start_sec`, `end_sec`) dla 8 gotowych shortów.
- Wygenerowanie metadanych SEO (tytuł max 45 zn, opis bez linków, hashtagi bez #Shorts, pinned comment) przez `/v1/shorts/describe`.
- Aktualizacja metadanych bezpośrednio na kanale YouTube (`Studio Prawy_PL`, `privacy: private` zachowane).

---

## 2. Zestawienie przetworzonych materiałów (8/8)

| Short ID | Source Video ID | Start (s) | End (s) | Status VSE | Status YT | Zoptymalizowany Tytuł (max 45 zn) |
|---|---|---|---|---|---|---|
| `slA15REfjpU` | `77ZwKDuOQ1M` | 723s | 773s | 200 OK | SUCCESS | Dualizm władzy niszczy Polskę od 1997 roku |
| `8nbA6YSZAVQ` | `77ZwKDuOQ1M` | 481s | 528s | 200 OK | SUCCESS | Gdyby PiS tak zrobiło - co by było?! |
| `mTyr64ygkJU` | `77ZwKDuOQ1M` | 640s | 693s | 200 OK | SUCCESS | Sejm to leniwe ciało - poseł odsłania |
| `9tjEXGE5sXg` | `77ZwKDuOQ1M` | 262s | 324s | 200 OK | SUCCESS | NGO-sy za pieniądze Tuska biły Nawrockiego |
| `FtQNSzHtQ0s` | `yM4IcLOobSI` | 641s | 690s | 200 OK | SUCCESS | Układ Rapallo: pakt antypolski 1922 |
| `mw6A9CZ6DuM` | `yM4IcLOobSI` | 269s | 312s | 200 OK | SUCCESS | Monachium 1938 – droga do wojny światowej |
| `ioObSLpRGc4` | `M3IUUo_3Nsc` | 50s | 92s | 200 OK | SUCCESS | Dwa pakty, które podzieliły Polskę 1939 |
| `lX2vvs8E-AY` | `l1bal_ucvFk` | 49s | 92s | 200 OK | SUCCESS | Jedwabne: Głazy i kontenery. Co dalej? |

---

## 3. Szczegóły wygenerowanych metadanych

### 1. `slA15REfjpU` (Polska konstytucja)
- **Tytuł:** `Dualizm władzy niszczy Polskę od 1997 roku`
- **Opis:** `Polski system polityczny cierpi na dualizm władzy wykonawczej od 1997 roku. Prezydent z wielkim mandatem społecznym a premier z realną władzą — to źródło ciągłych konfliktów. Czy potrzebujemy zmiany? Obserwuj @PrawyTV po więcej analiz!`
- **Tagi:** `#DualizmWładzy #SystemPolityczny #ReformaPaństwa #PrawoKonstytucyjne`
- **Przypięty komentarz:** `⚖️ Czy Polska potrzebuje silnego prezydenta czy silnego premiera? A może wystarczy wybrać JEDEN system zamiast mieszać oba? Całą rozmowę o reformie ustrojowej znajdziesz w powiązanym filmie poniżej! 👇`

### 2. `8nbA6YSZAVQ` (Organizacje Twój głos)
- **Tytuł:** `Gdyby PiS tak zrobiło - co by było?!`
- **Opis:** `Minister PSL dzwoni i grozi staroście za polubienie wpisu krytycznego wobec rządu. Afery powodziowe, nieprawidłowości w instytucjach - tylko dzięki niezależnym mediom to ujawniamy. Wyobraź sobie, co by było, gdyby tak działał PiS! Obserwuj @PrawyTV`
- **Tagi:** `#Polityka #KoalicjaObywatelska #PrawoiSprawiedliwość #PSL #NiezależneMedia`
- **Przypięty komentarz:** `🤔 Gdyby za rządów PiS minister zagroził staroście z opozycji - jaka byłaby reakcja mediów? Napiszcie w komentarzach! Całą rozmowę znajdziesz w powiązanym filmie poniżej 👇`

### 3. `mTyr64ygkJU` (Jestem zwolennikiem)
- **Tytuł:** `Sejm to leniwe ciało - poseł odsłania`
- **Opis:** `Poseł pierwszej kadencji bez ogródek: Sejm to leniwe ciało, rządzący uciekają od odpowiedzi. Czy potrzebujemy reformy trójpodziału władzy i niezależnego sądownictwa? Obserwuj @PrawyTV i dowiedz się więcej!`
- **Tagi:** `#PolskaPolityka #Sejm #TrójpodziałWładzy #ReformaSądownictwa`
- **Przypięty komentarz:** `😤 Czy zgadzasz się, że Sejm to „leniwe ciało" i potrzebujemy gruntownej reformy systemu? A może to przesada? Całą rozmowę o trójpodziale władzy i kulisach pracy parlamentu znajdziesz w powiązanym filmie poniżej! 👇`

### 4. `9tjEXGE5sXg` (Ten projekt był)
- **Tytuł:** `NGO-sy za pieniądze Tuska biły Nawrockiego`
- **Opis:** `Organizacje jak Twój Głos Jest Ważny i Akcja Demokracja otrzymywały fundusze ze spółek skarbu państwa i administracji. Te środki były wydatkowane na propagandę przeciwko Nawrockiemu i prawicy. Obserwuj @PrawyTV`
- **Tagi:** `#Nawrocki #propaganda #NGO #wybory2025 #PrawoiSprawiedliwość`
- **Przypięty komentarz:** `🎯 Czy finansowanie NGO-sów z publicznych pieniędzy to manipulacja wyborami? A może kolejne wybory będą jeszcze bardziej brutalne? Całą rozmowę znajdziesz w powiązanym filmie poniżej! 👇`

### 5. `FtQNSzHtQ0s` (Pakt z Niemcami w 1939)
- **Tytuł:** `Układ Rapallo: pakt antypolski 1922`
- **Opis:** `Polacy doskonale wiedzieli, co działo się w latach 1918-20. Niemcy i Sowieci chcieli nas zniszczyć. Układ w Rapallo z 1922 roku zacieśnił relacje między tymi państwami i był jawnie antypolski. Odrzucenie niemieckich żądań było jedyną możliwością. Obserwuj @PrawyTV`
- **Tagi:** `#UkładRapallo #HistoriaPolski #DwudziestolecieMiędzywojenne #Geopolityka #ZSRR`
- **Przypięty komentarz:** `🤔 Czy Polska w 1922 roku miała inną opcję niż odrzucenie paktu z wrogimi mocarstwami? A może powinniśmy byli spróbować dyplomacji? Całą rozmowę znajdziesz w powiązanym filmie poniżej! 👇`

### 6. `mw6A9CZ6DuM` (Konferencja Monachijska)
- **Tytuł:** `Monachium 1938 – droga do wojny światowej`
- **Opis:** `Konferencja monachijska 1938 – oddanie Sudetów Niemcom jako kluczowy moment na drodze do II wojny światowej. Czy historia się powtarza? Porównanie z działaniami Putinowskiej Rosji wobec krajów bałtyckich. Obserwuj @PrawyTV`
- **Tagi:** `#Monachium1938 #IIWojnaŚwiatowa #HistoriaPolityczna #Sudety`
- **Przypięty komentarz:** `⚠️ Czy oddanie Sudetów w 1938 było punktem bez powrotu do wojny? Czy dzisiaj powtarza się ten sam scenariusz z Rosją? Całą rozmowę znajdziesz w powiązanym filmie poniżej! 👇`

### 7. `ioObSLpRGc4` (Dla Rosji Putina)
- **Tytuł:** `Dwa pakty, które podzieliły Polskę 1939`
- **Opis:** `Pakt Ribbentrop-Mołotow z 23 sierpnia i 28 września 1939 - dwa akty rozbiorowe wobec Polski. Tajne protokoły Hitler-Stalin, które zmieniły bieg historii. Obserwuj @PrawyTV więcej!`
- **Tagi:** `#PaktMolotowRibbentrop #HistoriaPolski #Wrzesien1939 #IIWojnaSwiatowa #PrawyTV`
- **Przypięty komentarz:** `⚔️ Czy Polskę pogrzebały dwa pakty czy bierność Zachodu? Całą rozmowę znajdziesz w powiązanym filmie poniżej! 👇`

### 8. `lX2vvs8E-AY` (Złośliwi mówili)
- **Tytuł:** `Jedwabne: Głazy i kontenery. Co dalej?`
- **Opis:** `Organizator obchodów w Jedwabnem ujawnia plany! Od września cotygodniowe spotkania edukacyjne przy głazach i kontenerach. To nie sztuka dla sztuki - dowiedz się, jaki jest prawdziwy cel. Obserwuj @PrawyTV`
- **Tagi:** `#Jedwabne #HistoriaPolski #EdukacjaNarodowa #PamięćHistoryczna`
- **Przypięty komentarz:** `🤔 Czy systematyczne spotkania edukacyjne w Jedwabnem to właściwa droga do zachowania pamięci historycznej? A może to zbyt kontrowersyjne miejsce? Całą rozmowę o planach i celach znajdziesz w powiązanym filmie poniżej! 👇`
