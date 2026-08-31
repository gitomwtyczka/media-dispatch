# Raport: Profil portalu kurier365.pl i historia integracji PressAI

**Callsign:** media-analyst-kurier365  
**Data:** 2026-08-31 | **Workspace:** media-dispatch  
**Status:** Raport analityczny  

---

## 1. Profil portalu kurier365.pl

### Tematyka i pozycjonowanie
Kurier365.pl to wieloletni (aktywny od >2012 r., archiwum >87 tys. postów) serwis ogólnoinformacyjny o profilu gospodarczo-społecznym i poradnikowym. W ekosystemie ImpresjaPR pełni rolę medium „dla ludzi” (B2C / czytelnik masowy), stanowiąc lżejszy, konsumencki odpowiednik analitycznego portalu BiznesCiti.com.

- **Główne filary tematyczne:**
  - Gospodarka i finanse na co dzień (ceny, podatki, inflacja, finanse osobiste)
  - Społeczeństwo, rynek pracy, edukacja, zdrowie publiczne
  - Odpowiedzialny biznes (CSR, patronaty, nagrody pracodawców)
  - Lifestyle, turystyka, technologie użytkowe, kultura (np. recenzje komiksów/książek, wydarzenia)
- **Ton i styl:**
  - Przystępny, konkretny, poradnikowy (perspektywa: „Co to oznacza dla obywatela/konsumenta?”)
  - Formatowanie pod kątem zaangażowania i Google Discover (atrakcyjne leady, chwytliwe nagłówki bez taniego clickbaitu)
  - Formy dziennikarskie: news, poradnik, satelita Discover, wywiad/wideo, recenzja, explainer
- **Grupa docelowa:**
  - Konsumenci, pracownicy, drobni przedsiębiorcy, osoby szukające praktycznych informacji gospodarczo-społecznych
- **Kategorie i tagi:**
  - *Kategorie:* Gospodarka, Społeczeństwo, Biznes & CSR, Praca, Zdrowie, Technologie, Kultura & Styl, Finanse Osobiste
  - *Tagi:* formatowane z końcowym przecinkiem (np. `gospodarka, rynek pracy, finanse, prawo,`), semantyczne frazy LSI (7-10 per tekst)

---

## 2. Historia i stan integracji PressAI dla kurier365.pl

### Wykorzystywane silniki i narzędzia
1. **PressAI SaaS (`crimson-void` backend):**
   - Dedykowany wbudowany profil redakcyjny `Kurier365` w `routers/playbooks.py` oraz `ai_engine.py`
   - Reguły: proste słownictwo, nacisk na Google Discover, dozwolone emotikony w tytułach, wzajemny cross-linking z `biznesciti.com`
   - Generacja wielomodelowa: OpenAI (GPT-4o), Anthropic (Claude 3.5/3.7), Gemini (2.0/2.5 Flash & Pro)
2. **PressAI WordPress Plugin (`pressai-wp` v1.0.3):**
   - Integracja z edytorem Gutenberg (panel boczny, REST proxy, import do bloków `core/paragraph`, `core/heading`, `core/list`, `core/quote`)
   - Moduł *Content Retrofit* (automatyczne dogenerowywanie nagłówków H2/H3 i FAQ dla artykułów historycznych)
3. **VSE (Video SEO Engine) Integration:**
   - Wdrożona w maju 2026 integracja `create_wp_post()` (REST API)
   - Test produkcyjny: konwersja zewnętrznych wideo z YouTube (np. Mazurek, recenzje kulturalne) na artykuły z transkrypcją, rozdziałami czasowymi i FAQ (posty WP#87358, 87361, 87364)
   - Dodany profil portalu `kurier365` do bazy VSE (`wp_portals`)

### Co działało dobrze, a co wymaga poprawy
- ✅ **Mocne strony:** Kompletny standard HTML (lead `<p class="lead">`, `<!--more-->`, min. 3 nagłówki H3, FAQ Schema JSON-LD, metadane grafik, brak halucynacji URL-i).
- ⚠️ **Wyzwania / Ryzyka:**
  - *Google SERP cache:* Stare posty (np. z 2012 r.) z dynamicznym widgetem „Świeże” potrafiły przejąć snippety nowych artykułów (wymagana kontrola indeksacji w GSC).
  - *Auth pluginu:* Przejście z JWT (wygasa po 7 dniach) na stabilny License Key (API Key).

---

## 3. Rekomendacja dla codziennej produkcji (media-dispatch)

### Sugerowany wolumen i harmonogram
- **Rekomendowana częstotliwość:** **3 – 6 artykułów dziennie** (tryb stabilny, bez kanibalizacji i ryzyka spamu w Discover).
- **Rozkład w ciągu dnia:**
  - `07:30 – 08:30` — Poranny news/poradnik konsumencki (optymalizacja pod Discover na dojazdy)
  - `11:30 – 13:00` — Analiza rynkowa / gospodarka / praca
  - `16:00 – 17:30` — Popołudniowy materiał lifestylowy / zdrowie / społeczeństwo
  - `19:00 – 20:30` — Recenzja, wideo-artykuł (VSE) lub felieton

### Źródła wejściowe
1. **Feed Crawler (RSS):** Agregacja komunikatów PAP, portali branżowych, serwisów urzędowych (ZUS, MF, UOKiK) i Google Alerts.
2. **Content Radar / Google Trends:** Identyfikacja nagłych trendów i pytań użytkowników („co to jest...”, „od kiedy...”).
3. **VSE Pipeline (Wideo → Tekst):** Wartościowe wywiady, debaty gospodarcze i podcasty YouTube przetwarzane na artykuły z FAQ i rozdziałami.
4. **Tematy autorskie / PR:** Komunikaty prasowe i materiały partnerskie (CSR / patronaty).

### Proponowany flow produkcyjny
```
[Feed Crawler / Trends / VSE] 
       ↓
[Redaktor Naczelny (AI)] — selekcja 5-8 propozycji rano
       ↓
[Zatwierdzenie przez Redaktora / GO] (1-klik w panelu lub Discord/Telegram)
       ↓
[PressAI Worker] — generacja artykułu z playbookiem Kurier365 (SEO + FAQ + JSON-LD)
       ↓
[WordPress Publisher] — publikacja jako DRAFT lub SCHEDULED POST
       ↓
[Quality Gate / Social Publisher] — publikacja na portalu + feed social
```

---

## 4. Otwarte pytania do Redakcji / Użytkownika

1. **Tryb publikacji:** Czy artykuły wygenerowane przez media-dispatch mają trafiać od razu jako `publish` (pełna automatyzacja), czy jako `draft` do 1-kliknięciowej akceptacji człowieka?
2. **Konta i dostęp WordPress:** Czy do publikacji przez PressAI/media-dispatch dedykujemy osobne konto redakcyjne (np. `Redakcja Kurier365` / `AI Assistant`) z Application Password?
3. **Materiały graficzne:** Czy miniatury i zdjęcia w artykułach pobieramy automatycznie (z RSS/Unsplash/DALL-E/YouTube thumb), czy korzystamy z banku zdjęć redakcji?
4. **Cross-linking:** Czy potwierdzamy regułę twardego cross-linkingu z `biznesciti.com` w materiałach gospodarczych?
5. **Priorytety tematyczne na start:** Od którego filaru zaczynamy (poradniki finansowo-prawne, newsy gospodarcze, czy materiały wideo z kanałów YT)?

---
*[media-analyst-kurier365 | media-dispatch 31.08.2026]*
