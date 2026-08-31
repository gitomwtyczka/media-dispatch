# Profil Portalu BiznesCiti.com & Historia Produkcji PressAI

> **Autor:** [media-analyst | media-dispatch 31.08.2026]  
> **Cel:** Budowa profilu portalu do codziennej, autonomicznej produkcji artykułów w ekosystemie `media-dispatch` / PressAI.  
> **Wydawca:** Impresja PR (Grupa Medialna: BiznesCiti.com, Kurier365.pl, RaportCSR.pl, Prawy.pl)

---

## 1. Profil Portalu BiznesCiti.com

### Tematyka i specjalizacja
- **Główny profil:** Branżowo-biznesowy portal analityczno-informacyjny o profilu B2B / makroekonomicznym.
- **Specjalizacje tematyczne:**
  - **ESG / CSR i Zrównoważony Rozwój:** Regulacje unijne (CSRD, CSDDD, AI Act), raportowanie niefinansowe, kongresy ESG, etyka biznesu.
  - **Menedżerowie i Liderzy Branżowi:** Personalizacja biznesu, rankingi wpływowych postaci (np. Lista 100/50 w turystyce, ranking PR Check), sylwetki liderów, wywiady.
  - **Rynek Usług Profesjonalnych i Komunikacja:** Branża PR, marketing B2B, patronaty medialne forów i kongresów gospodarczych.
  - **Innowacje, Przemysł i Nowe Technologie:** Przemysł obronny/dronowy (np. Śląskie Dni Lotnictwa i Dronów), technologie żywności funkcjonalnej, energetyka i transformacja.
  - **Po godzinach / Lifestyle B2B:** Niszowe innowacje regionalne, kulinaria i turystyka biznesowa przedstawiane przez pryzmat rozwoju rynku.
- **Wymiar lokalno-regionalny vs ogólnokrajowy:** Portal nie jest lokalnym informatorem miejskim, lecz łączy ogólnopolski/europejski kontekst makro z regionalnymi studiami przypadków (np. firmy ze Śląska, Małopolski, Podkarpacia, inwestycje samorządowe).

### Ton i styl
- **Ton:** Profesjonalny, merytoryczny, ekspercki, rzeczowy, pozbawiony taniej sensacji.
- **Styl:** Analityczny, oparty na twardych danych liczbowych, cytatach ekspertów, stanowiskach organizacji branżowych i instytucji.
- **Struktura artykułów:** Zwięzłe leady informacyjne (250–350 znaków), logiczny podział nagłówkami `<h3>`/`<h4>`, ramki kontekstowe (`<aside class="context-box">`: pojęcie, osoba, prawo, dane), sekcje Q&A / FAQ.

### Grupy docelowe
- Menedżerowie C-level, dyrektorzy operacyjni, specjaliści ds. ESG/CSR i compliance.
- Właściciele firm MŚP, przedsiębiorcy szukający wiedzy o regulacjach i trendach rynkowych.
- Środowisko agencji PR, marketingu, branży turystycznej i eventowej (MICE).
- Inwestorzy, analitycy i samorządowcy śledzący innowacje gospodarcze.

### Kategorie priorytetowe
1. `CSR / ESG` (Zrównoważony rozwój, regulacje, kongresy)
2. `Biznes i Gospodarka` (Regulacje sektorowe, rynki, finanse przedsiębiorstw, prawo)
3. `Menadżerowie / Liderzy` (Wywiady, rankingi, nominacje, sylwetki)
4. `Innowacje & Technologie` (Drony, przemysł, AI, transformacja cyfrowa)
5. `Wydarzenia & Patronaty` (Fora gospodarcze, relacje z kongresów, konkursy)
6. `Po godzinach` (Turystyka biznesowa, innowacje konsumenckie)

---

## 2. Historia PressAI dla BiznesCiti.com

### Jakie typy artykułów generowano
- **Wbudowane profile systemowe (`BUILTIN_PROFILES["BiznesCiti"]` w `crimson-void`):**
  - Ciężkie analizy rynkowe, raporty sektorowe, explainery biznesowe.
  - Artykuły typu Hub & Satellite — połączone z relacjami z podcastów i wideo.
- **Formaty zdefiniowane w `article_formats.yaml`:**
  - *Publicystyczne:* `analiza` (quick pick), `komentarz` (editorial), `felieton` (autorski z mocną puentą).
  - *Użytkowe:* `explainer` (tłumaczenie regulacji i procesów), `casestudy` (studia wdrożeń), `factcheck`.
  - *Informacyjne:* `news`, `brief` (do 300 słów), `sprawozdanie` (relacje chronologiczne), `update`.
  - *Wideo/Satelity:* `video_satellite` (artykuł towarzyszący wideo z interaktywnymi rozdziałami `seekTo` i schematem `VideoObject`).

### Źródła wejściowe
- Komunikaty prasowe i oświadczenia instytucji/firm (in extenso z autorskim opakowaniem SEO).
- Transkrypcje wystąpień i materiałów wideo z YouTube (VSE / Whisper → czyszczenie → generowanie artykułu).
- Raporty branżowe, wyniki badań rynkowych, zestawienia rankingowe (np. PR Check, WaszaTurystyka).
- Notatki z konferencji i kongresów gospodarczych.

### Szablony i prompty redakcyjne
- **Zasada Cross-linkingu:** Obowiązkowe wzajemne linkowanie z `Kurier365.pl` (BiznesCiti = analityczny hub B2B, Kurier365 = lżejszy satelita Discover/konsumencki).
- **Struktura 5 bloków:** HTML artykułu (z `<hr id="system-readmore" />`), Blok FAQ HTML (`<h2>`/`<h3>`), JSON-LD FAQPage, Blok Video HTML (`<figure>` + `<figcaption>` + timestampy), JSON-LD VideoObject/ImageObject.
- **Rygor antyhalucynacyjny:** Bezwzględny zakaz wymyślania danych, liczb, ekspertów czy fałszywych instytucji. Jeśli w materiale źródłowym brak nazwiska eksperta, stosowana jest parafraza z atrybucją źródła.
- **SEO & NLP:** Fraza główna w tytule, leadzie (pierwsze 100 słów), nagłówkach `<h3>` i meta-description (do 160 znaków); gęstość frazy 0,5%–2%.

### Efektywność i dotychczasowe wdrożenia
- **A/B Testing & Quality Gate:** Skrypt `auto_gen_ab.py` przetestował modele (GPT-4o, Claude Sonnet, Gemini Flash) pod kątem zgodności z Quality Gate (skala 0–15 pkt). Gemini Flash i GPT-4o osiągają wysoką stabilność formatowania HTML/Schema.
- **Infrastruktura VSE (Fix 30.06.2026):** Naprawiono obsługę tekstowego `portal_id = "biznesciti"` w bazie PostgreSQL `vse-postgres` oraz na frontendzie `vse-web`.
- **Universal Video SEO Pipeline (`shadow-perihelion`):** Przygotowano moduł `video_seo_tool.py` z obsługą portalu `biznesciti` do automatycznej publikacji postów formatu `video` (Gutenberg HTML + VideoObject).

---

## 3. Rekomendacja dla Codziennej Produkcji

### Ile artykułów dziennie
- **Rekomendowany wolumen:** **4–6 artykułów dziennie** (pn–pt) + **1–2 w weekendy**.
  - **1x Pogłębiona Analiza / Explainer / Case Study** (800–1200 słów) — główny materiał dnia (poranek 7:30–8:30).
  - **2x Newsy / Briefy gospodarcze / ESG / Regulacje** (400–600 słów) — publikowane w ciągu dnia (11:00, 14:00).
  - **1–2x Video Satellite / Podcast Explainer** (z materiałów wideo ekosystemu lub patronatów) — (16:00–18:00).
  - **1x Sylwetka / Wywiad / Relacja z wydarzenia** (co drugi dzień).

### Źródła wejściowe (Media-Dispatch Architecture)
1. **Warstwa 1 (Intelligence):**
   - `feed-crawler-worker` — monitoring branżowych RSS (PAP Biznes, CIRE, WNP, Forsal, prawo.pl, portale ESG/unijne).
   - `content-radar-worker` — monitoring Google Trends (frazy biznes/regulacje/praca/podatki) oraz kanałów Telegram.
2. **Warstwa 2 (Editorial — Redaktor Naczelny):**
   - Selekcja tematów dnia o najwyższym potencjale B2B i dopasowanie do profilu BiznesCiti.
   - Parowanie tematów dla tandemu BiznesCiti (analityka) ↔ Kurier365 (Discover / konsumencki).
3. **Warstwa 3 (Production):**
   - `pressai-worker` — automatyczny drafting artykułów tekstowych z Quality Gate.
   - `vse-worker` — automatyczna obróbka wideo/podcastów gospodarczych (Whisper → SEO HTML + schema).
4. **Warstwa 4 (Distribution):**
   - `wp-publisher` — wysyłka draftów via WP REST API do WordPress (`https://biznesciti.com`).

### Macierz Kategorii i Formatów

| Kategoria WP | Format preferowany | Źródło wejściowe | Kadencja |
|---|---|---|---|
| **CSR / ESG** | Analiza / Explainer | Raporty, regulacje UE, komunikaty kongresowe | 1x dziennie |
| **Gospodarka / Prawo** | News / Brief / Fact-check | Feed Crawler (RSS), orzeczenia, ustawy | 2x dziennie |
| **Technologie / Przemysł** | Case Study / Artykuł z Wideo | VSE (YouTube/podcasty), relacje targowe | 1x dziennie |
| **Menedżerowie / PR** | Wywiad / Sylwetka / Ranking | Informacje agencyjne, PR Check, nominacje | 2–3x w tygodniu |
| **Po godzinach** | Feature / Poradnik biznesowy | Trendy rynkowe, turystyka biznesowa | 2x w tygodniu |

### Flow produkcji i zatwierdzania
1. **Crawl & Rank:** Feed Crawler identyfikuje temat → scoring merytoryczny B2B.
2. **Draft Generation:** PressAI generuje artykuł w standardzie 5 bloków HTML/Schema z weryfikacją Quality Gate.
3. **Cross-Link Injection:** Wstrzyknięcie min. 2 linków wewnętrznych oraz odnośnika do artykułu uzupełniającego na Kurier365.pl.
4. **Staging / Status w WP:** Tworzenie wpisu ze statusem `draft` (lub `pending`).
5. **Human-in-the-Loop:** Redaktor zatwierdza lub edytuje draft jednym kliknięciem w WP Admin / Dashboard VSE.

---

## 4. Otwarte Pytania i Wymagane Ustalenia

1. **Credentials WordPress dla BiznesCiti:**
   - Czy portal `biznesciti.com` posiada wygenerowane konto API (`Application Password`) dla workera `wp-publisher`? (W rejestrze widniał status `TO_FILL`).
2. **Harmonogram Cross-Linkingu Kurier365 ↔ BiznesCiti:**
   - Czy tandem produkcyjny ma być uruchamiany symultanicznie (jeden temat generuje jednocześnie news Discover dla Kurier365 i analizę B2B dla BiznesCiti)?
3. **Kanały wideo dedykowane dla BiznesCiti:**
   - Czy oprócz Prawy TV i Prawy Biblijny planowane jest podpięcie dedykowanego kanału YouTube/podcastu o tematyce gospodarczej/PR pod VSE dla BiznesCiti?
4. **Repozytorium mediów graficznych:**
   - Jakie jest źródło grafik wyróżnionych (Unsplash API, baza własna Impresja PR, generatory AI Imagen/Midjourney)?
