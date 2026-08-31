# Specyfikacja Źródeł i Flow Redakcyjnego: Kurier365.pl & BiznesCiti.com

> **Autor:** `[media-analyst-editorial | media-dispatch 31.08.2026]`  
> **Status:** Specyfikacja techniczno-operacyjna  
> **Repozytorium:** `media-dispatch`  
> **Portale docelowe:** `kurier365.pl`, `biznesciti.com` (współpraca z `prawy.pl`)  

---

## 1. Wstęp i Cel Dokumentu

Niniejszy dokument stanowi pełną specyfikację techniczną i redakcyjną dla zautomatyzowanego pozyskiwania tematów (Ingest Intelligence), ich selekcji przez **Redaktora Naczelnego AI** oraz dystrybucji zadań produkcyjnych do silnika **PressAI** dla dwóch kluczowych portali Grupy Impresja PR:
1. **Kurier365.pl** — medium ogólnoinformacyjne, poradnikowe, społeczno-gospodarcze i konsumenckie (B2C, zoptymalizowane pod Google Discover).
2. **BiznesCiti.com** — analityczny portal B2B, makroekonomia, regulacje, ESG, technologie i rynki kapitałowe.

Dokument precyzuje źródła danych, architekturę dedykowanych workerów ingestu, metody autoryzacji i scrapingu, reguły filtrowania merytorycznego oraz optymalny wewnętrzny kanał decyzyjny (Human-in-the-Loop).

---

## 2. Specyfikacja Źródeł Wejściowych (Sources Config)

### 2.1. KURIER365.PL — Specyfikacja Źródeł

Portal `kurier365.pl` opiera się na miksie komunikatów agencyjnych, stałych autorów zewnętrznych, oficjalnych komunikatów urzędowych (UOKiK) oraz agregacji RSS (dział Nauka i działy ogólne).

```
                            [ŹRÓDŁA KURIER365.PL]
 ├── Gmail (tobroz@gmail.com) ──┬── WEI (Warsaw Enterprise Institute)
 │                              ├── Cezary Rudiński (Turystyka / 2 adresy / selekcja foto)
 │                              ├── Arkadiusz Bińczyk (Publicystyka / 3 adresy)
 │                              ├── Wydawnictwo Biały Kruk (Kultura / Książki)
 │                              └── Ogólne komunikaty PR / załączniki PDF/DOCX
 ├── Newseria ─────────────────── Depesze agencyjne, multimedia (wideo/audio)
 ├── Feed Crawler (RSS) ───────── Dział NAUKA + działy ogólnotematyczne
 └── Komunikaty Urzędowe ─────── UOKiK (Kluczowe decyzje i ostrzeżenia konsumenckie)
```

#### Tabela Konfiguracyjna Źródeł — Kurier365.pl:

| Źródło | Typ Ingestu | Priorytet | Uwagi Implementacyjne & Routing | Wymagana Selekcja? |
|---|---|---|---|---|
| **UOKiK (Komunikaty Urzędowe)** | Web Scraper / RSS BIP UOKiK | **Krytyczny (P0)** | Bezwzględny priorytet konsumencki. Monitorowanie decyzji Prezesa UOKiK, kar, klauzul niedozwolonych i ostrzeżeń konsumenckich. Format: Alert Konsumencki + Poradnik Discover. | **Automatyczna kwalifikacja (P0)** → natychmiastowy kandydat w kolejce RN. |
| **Cezary Rudiński** | Gmail API (`tobroz@gmail.com`) | **Wysoki (P1)** | Dział Turystyka/Krajoznawstwo. Autor wysyła maile z 2 adresów. Zawiera obszerne teksty oraz dużą liczbę zdjęć w załącznikach. Wymaga dedykowanego modułu `photo-curator` (wybór 4–6 ujęć, konwersja WebP, opisy ALT). | **WYMAGANA SELEKCJA PÓŁAUTOMATYCZNA** (selekcja zdjęć i strukturyzacja nagłówków). |
| **Arkadiusz Bińczyk** | Gmail API (`tobroz@gmail.com`) | **Wysoki (P1)** | Publicystyka, historia, felietony, sprawy społeczne. Wiadomości spływają z co najmniej 3 różnych adresów e-mail. Parsowanie treści maila oraz załączników `.docx`/`.pdf`. | **Półautomatyczna** (weryfikacja kategoryzacji WP i dopasowania tytułu). |
| **WEI (Warsaw Enterprise Institute)** | Gmail API (filtr domeny `@wei.org.pl`) | **Wysoki (P1)** | Analizy wolnorynkowe, gospodarka, podatki, komentarze eksperckie. Ekstrakcja tez głównych i generowanie przystępnego omówienia pod kątem czytelnika masowego. | **Półautomatyczna** (selekcja tez pod Discover / format Q&A). |
| **Biały Kruk** | Gmail API (domena `@bialykruk.pl`) | **Średni (P2)** | Materiały wydawnicze, kultura, historia, recenzje książkowe, fragmenty publikacji. Ekstrakcja okładek i not biograficznych autorów. | **Półautomatyczna** (przypisanie do działu Kultura/Historia). |
| **Newseria (Ogólna / Lifestyle / Innowacje)** | Web Scraping po zalogowaniu | **Średni (P2)** | Depesze agencyjne, wywiady, wideo/audio. Wykorzystanie konta redakcyjnego (login/hasło). Selekcja tematów społecznych, konsumenckich i technologicznych. | **Automatyczna wstępna** + zatwierdzenie w Telegramie. |
| **Dział NAUKA (RSS Feed Crawler)** | RSS / Atom Crawler | **Średni (P2)** | Monitoring serwisów naukowych (PAP Nauka w Polsce, serwisy uczelniane, czasopisma popularnonaukowe). Tłumaczenie żargonu akademickiego na format popularnonaukowy. | **Automatyczna** (ranking merytoryczny i potencjał Discover). |
| **Każdy inny dział (RSS Feed Crawler)** | RSS / Atom Crawler | **Normalny (P3)** | Ogólny monitoring 30-minutowy (społeczeństwo, rynek pracy, CSR, zdrowie, kultura). | **Automatyczna** (scoring merytoryczny i deduplikacja). |
| **Gmail tobroz@gmail.com (Pozostałe PR)** | Gmail API | **Normalny (P3)** | Standardowe komunikaty agencji PR, informacje prasowe firm. Filtr antyspamowy i scoring jakościowy. | **Automatyczna selekcja** (odrzucanie spamu i czystej reklamy). |

---

### 2.2. BIZNESCITI.COM — Specyfikacja Źródeł

Portal `biznesciti.com` pozycjonowany jest jako analityczny hub B2B. Wymaga twardych danych makroekonomicznych, informacji ze spółek, analizy geopolityki i surowców oraz precyzyjnego filtrowania treści agencyjnych.

```
                            [ŹRÓDŁA BIZNESCITI.COM]
 ├── ISBNews ──────────────────── Źródło pierwotne: depesze giełdowe, makro, wyniki
 ├── Polskie Portale Biznesowe ── Benchmarking & odniesienie (Bankier, Money, WNP, CIRE)
 ├── Global & European Business ── FT, Bloomberg, Reuters, Politico Europe (wpływ na rynek)
 ├── Zagrożenia Wojenne/Globalne ─ Wpływ konfliktów na łańcuchy dostaw, surowce, inflację
 ├── Daleki Wschód ────────────── Nikkei Asia, SCMP, Caixin (technologie, półprzewodniki)
 └── Newseria Biznes ──────────── Ekstrakcja z filtrem ANTY-EKO-IDEOLOGII (Neutrality Gate)
```

#### Tabela Konfiguracyjna Źródeł — BiznesCiti.com:

| Źródło | Typ Ingestu | Priorytet | Uwagi Implementacyjne & Routing | Wymagana Selekcja? |
|---|---|---|---|---|
| **ISBNews** | RSS / API / Depesze | **Krytyczny (P0)** | Główne źródło pierwotne. Depesze gospodarcze, komunikaty spółek giełdowych, stopy procentowe, PKB, inflacja. Błyskawiczna synteza do formatu analitycznego B2B. | **Półautomatyczna** (selekcja kluczowych spółek i wskaźników makro). |
| **Zagrożenia gospodarcze z zawirowań wojennych** | Multi-source RSS & Intelligence | **Wysoki (P1)** | Globalne monitorowanie wpływu wojen i napięć geopolitycznych: szlaki handlowe (Czerwone Morze, Cieśnina Ormuz), ceny ropy/gazu/metali, sankcje, przemysł zbrojeniowy. | **Merytoryczna selekcja** (eliminacja propagandy, skupienie na bilansie zysków/strat rynkowych). |
| **Polskie portale biznesowe (PL Reference)** | RSS Crawler / Content Radar | **Średni (P2)** | Money.pl, Business Insider, Bankier.pl, Parkiet, Forsal, WNP, CIRE. Służą jako benchmarking i wykrywanie trendów rynkowych (nie kopiujemy, lecz uzupełniamy o autorskie analizy). | **Automatyczny clustering tematów** (wykrywanie luk informacyjnych). |
| **Europejskie i światowe portale biznesowe** | RSS / Multi-lingual Scraper | **Średni (P2)** | Financial Times, Bloomberg, Reuters, Handelsblatt, Les Echos, Politico Europe. Tłumaczenie i adaptacja do polskich realiów gospodarczych oraz regulacji UE (CSRD, ETS, AI Act). | **Selektywna** (tematy wpływające bezpośrednio na polskie przedsiębiorstwa). |
| **Daleki Wschód (Azja / Pacyfik)** | RSS / Curated Feeds (kadencja 2–3x w tyg.) | **Średni/Niski (P3)** | Nikkei Asia, South China Morning Post, Caixin, Yonhap. Trendy w półprzewodnikach, elektromobilności, surowcach ziem rzadkich i logistyce morskiej. | **Selektywna** (tylko tematy o strategicznym znaczeniu makro). |
| **Newseria Biznes / Innowacje** | Web Scraping po zalogowaniu | **Średni (P2)** | Pobieranie depesz biznesowych i wypowiedzi ekspertów. **UWAGA:** Wymagany rygorystyczny filtr neutralności (Eco-Bias Gate). | **OBOWIĄZKOWY FILTR AI (Eco-Bias Gate)** — odrzucenie narracji ideologicznych. |

---

## 3. Analiza Źródła Newseria i Integracja Techniczna

### 3.1. Dostępność API vs Scraping Sesyjny
Serwis `newseria.pl` jest agencją informacyjną dedykowaną dla akredytowanych redakcji. Na podstawie analizy technicznej:
- **Brak otwartego publicznego API:** Newseria nie oferuje publicznego REST API w modelu self-service.
- **Konto Redakcyjne (Login/Hasło):** Redakcja posiada aktywne konto z uprawnieniami do pobierania pełnych treści, plików wideo HD, ścieżek audio oraz zdjęć prasowych.
- **Implementacja konektora (`newseria-connector`):**
  1. **Zarządzanie sesją:** Moduł w Pythonie (`playwright` w trybie headless lub `httpx.AsyncClient` z obsługą cookies).
  2. **Endpoint logowania:** `POST https://newseria.pl/logowanie` (obsługa tokenów CSRF, sesyjnych ciasteczek i mechanizmu keep-alive).
  3. **Polling działów:** Okresowe skanowanie sekcji:
     - `https://biznes.newseria.pl` (dla BiznesCiti i Kurier365)
     - `https://innowacje.newseria.pl` (dla obu portali)
     - `https://lifestyle.newseria.pl` (dla Kurier365)
  4. **Ekstrakcja danych:** Tytuł, data, lead, transkrypcja wypowiedzi, dane eksperta/instytucji, lista powiązanych plików multimedialnych.

### 3.2. Filtrowanie Treści: Eco-Bias & Neutrality Gate (BiznesCiti)
Redakcja zdefiniowała jednoznaczne wytyczne: **unikamy skrajnie politycznych treści biznesowych, w których ekologia jest jednostronnie przedstawiana jako jedyne i bezdyskusyjne rozwiązanie problemów świata**, bez uwzględnienia kosztów gospodarczych, konkurencyjności przemysłu i twardego rachunku ekonomicznego.

#### Mechanizm Filtrujący AI (`Eco-Bias Classifier`):
Każdy materiał pobrany z Newserii przed skierowaniem do kolejki BiznesCiti przechodzi przez automatyczną ewaluację LLM:

```
[Nowa depesza Newseria] ──► [Eco-Bias Classifier (Gemini Flash)]
                                    │
    ┌───────────────────────────────┴───────────────────────────────┐
    ▼                                                               ▼
[eco_bias_score > 60]                                    [eco_bias_score <= 60]
    │                                                               │
    ├─► Czy materiał ma wartość merytoryczną?                       ▼
    │    ├── NIE ──► [ODRZUĆ / STATUS: REJECTED_ECO_BIAS]     [ZAAKCEPTOWANY]
    │    └── TAK ──► [PRZEPISZ: Zderz z kosztami rynkowymi]         │
    │                                                               ▼
    └─────────────────────────────────────────────────────► [Kolejka Redaktora Naczelnego]
```

**Kryteria oceny algorytmicznej:**
1. **Analiza jednostronności:** Czy artykuł postuluje wprowadzenie zakazów lub obciążeń bez podania kosztów finansowych dla firm/obywateli?
2. **Obecność twardych danych:** Czy materiał opiera się na wyliczeniach rynkowych i inżynieryjnych, czy wyłącznie na deklaracjach wizerunkowych (greenwashing)?
3. **Akcja naprawcza:** Jeśli temat jest istotny rynkowo, ale skrajnie skrzywiony ideologicznie, prompt PressAI otrzymuje dyrektywę: *"Przepisz materiał w tonie analitycznym, uzupełnij o perspektywę kosztową i wyzwania konkurencyjności europejskiego przemysłu"*.

---

## 4. Flow Redaktora Naczelnego AI — Kanał Wewnętrzny

### 4.1. Porównanie Opcji Kanału Decyzyjnego

| Parametr | Opcja A: Telegram Bot (Rekomendowane MVP) | Opcja B: Google Sheets (Control Center) | Opcja C: Dedykowana WebApp |
|---|---|---|---|
| **Czas wdrożenia (Time-to-Value)** | 🟢 **1–2 dni robocze** | 🟡 3–4 dni robocze | 🔴 2–3 tygodnie |
| **UX na urządzeniach mobilnych** | 🟢 **Idealny** (natywne powiadomienia push, 1-tap akcje) | 🟡 Uciążliwy (wymaga otwierania arkusza na telefonie) | 🟡 Wymaga logowania w przeglądarce |
| **Szybkość podejmowania decyzji** | 🟢 **Błyskawiczna** (średnio 5–10 sekund na kandydata) | 🟡 Średnia (ręczne przełączanie dropdownów) | 🟢 Dobra |
| **Dwukierunkowa interakcja (Uwagi)** | 🟢 **Natywna** (odpowiedź tekstem/głosem w czacie bota) | 🔴 Słaba (wpisywanie tekstu w małą komórkę) | 🟢 Dobra (formularz uwag) |
| **Odporność na awarie i limity API** | 🟢 Bardzo wysoka (Telegram Bot API) | 🔴 Ryzyko rate-limitów Google Sheets API | 🟢 Wysoka |

### 4.2. Rekomendacja Architektoniczna: Telegram Bot (`redaktor-naczelny-bot`)

Rekomendujemy **Telegram Bot** jako główny interfejs operacyjny Redaktora Naczelnego, wsparty lokalną bazą SQLite (`shared/state/editorial_queue.db`) oraz rejestrem publikacji.

#### Format Prezentacji Kandydata w Telegramie:

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📰 [KURIER365.PL] Kandydat do publikacji #K-1042
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 Tytuł: UOKiK nakłada 14 mln zł kary na operatora telekomunikacyjnego
🏢 Źródło: Oficjalny Komunikat UOKiK | Priorytet: P0 (Krytyczny)
⏱ Data ingestu: 31.08.2026 14:30 | Dział docelowy: Prawo & Finanse

📝 Resume redakcyjne (260 znaków):
Prezes UOKiK ukarał operatora za bezprawne włączanie płatnych pakietów subskrypcyjnych bez wyraźnej zgody abonentów. Decyzja nakazuje zwrot nienależnie pobranych środków dla ponad 250 tys. klientów oraz zmianę regulaminu.

🎯 Sugerowany format PressAI: Alert Konsumencki + Poradnik Discover (FAQ JSON-LD)
🔗 Link do źródła: https://uokik.gov.pl/aktualnosci/komunikat-1042

Wybierz akcję redakcyjną poniżej:
```

#### Przyciski Inline pod wiadomością:
```
[ ✅ Akceptuj (Generuj Draft WP) ]    [ ❌ Odrzuć ]
[ ⏰ Odrocz D+1 (Jutro rano) ]        [ ⏰ Odrocz D+7 (Za tydzień) ]
[ 💬 Dodaj uwagi redakcyjne ]
```

#### Logika obsługi akcji redaktora:
1. **`✅ Akceptuj`**:
   - Bot zmienia status kandydata na `approved`.
   - Wysyła task do kolejki `pressai-worker` z przypisanym playbookiem portalu.
   - `pressai-worker` generuje artykuł w standardzie 5 bloków HTML + SEO i tworzy wpis `draft` w WordPressie.
   - Bot aktualizuje wiadomość na Telegramie: `✅ ZAAKCEPTOWANO -> Artykuł utworzony w WP jako DRAFT (ID: #87490) w 48s`.
2. **`❌ Odrzuć`**:
   - Status zmieniony na `rejected`. Wiadomość oznaczana jako `❌ ODRZUCONO`.
3. **`⏰ Odrocz D+1 / D+7`**:
   - Kandydat otrzymuje timestamp wznowienia (`wake_up_at = now() + 24h / 7d`).
   - Wiadomość znika lub otrzymuje status `⏰ ODROCZONO DO [DATA]`.
4. **`💬 Dodaj uwagi redakcyjne`**:
   - Bot wysyła prompt: *"Napisz lub podyktuj uwagi dla PressAI (np. 'Zwróć uwagę na instrukcję jak odzyskać pieniądze z reklamacji'):"*.
   - Redaktor wysyła wiadomość tekstową w odpowiedzi.
   - Bot zapisuje uwagę w `custom_instructions` kandydata i automatycznie zatwierdza zlecenie do PressAI z uwzględnieniem tych wytycznych.

---

## 5. Specyfikacja Gmail Workers i Rozpoznawanie Nadawców

### 5.1. Moduł `gmail-kurier365-worker`
Worker działający w pętli (cron co 15–30 minut) podpięty pod skrzynkę `tobroz@gmail.com` za pośrednictwem Gmail API (`oauth2` / Service Account lub token offline).

#### Konfiguracja Reguł Rozpoznawania Nadawców (`shared/config/gmail_rules.json`):

```json
{
  "rules": [
    {
      "source_id": "cezary_rudinski",
      "display_name": "Cezary Rudiński (Turystyka)",
      "target_portal": "kurier365",
      "category": "Turystyka & Podróże",
      "matching_emails": [
        "c.rudinski@poczta.onet.pl",
        "cezary.rudinski@gmail.com"
      ],
      "signature_fallback": ["Cezary Rudiński", "Cezary Rudinski"],
      "requires_photo_curation": true,
      "priority": "P1"
    },
    {
      "source_id": "arkadiusz_binczyk",
      "display_name": "Arkadiusz Bińczyk (Publicystyka)",
      "target_portal": "kurier365",
      "category": "Kultura & Społeczeństwo",
      "matching_emails": [
        "arkadiusz.binczyk@wp.pl",
        "a.binczyk@media.pl",
        "abinczyk@interia.pl"
      ],
      "signature_fallback": ["Arkadiusz Bińczyk", "Arkadiusz Binczyk"],
      "requires_photo_curation": false,
      "priority": "P1"
    },
    {
      "source_id": "wei_agency",
      "display_name": "Warsaw Enterprise Institute",
      "target_portal": "kurier365",
      "category": "Gospodarka",
      "matching_domains": ["wei.org.pl"],
      "priority": "P1"
    },
    {
      "source_id": "bialy_kruk",
      "display_name": "Wydawnictwo Biały Kruk",
      "target_portal": "kurier365",
      "category": "Kultura & Historia",
      "matching_domains": ["bialykruk.pl"],
      "priority": "P2"
    },
    {
      "source_id": "uokik_mail",
      "display_name": "UOKiK Informacje Prasowe",
      "target_portal": "kurier365",
      "category": "Konsument & Prawo",
      "matching_domains": ["uokik.gov.pl"],
      "priority": "P0"
    }
  ]
}
```

### 5.2. Obsługa Przypadków Specjalnych

#### 1. Cezary Rudiński — Moduł Selekcji Zdjęć (`photo-curator`):
- **Specyfika:** Maile od p. Cezarego Rudińskiego zawierają relacje podróżnicze oraz paczki od 8 do 30 zdjęć o wysokiej rozdzielczości (często prosto z aparatu).
- **Proces automatyczny:**
  1. Pobranie wszystkich załączników graficznych do folderu tymczasowego.
  2. **Filtr jakościowy:** eliminacja zdjęć nieostrych, o złym naświetleniu lub zbyt małej rozdzielczości.
  3. **Wybór reprezentatywny:** Wybór **4–6 najlepszych kadrów** prezentujących różne plany (szeroki kadr na zabytek/krajobraz, detal architektoniczny, ujęcie klimatyczne).
  4. **Konwersja:** Przekształcenie do formatu WebP (kompresja 82%, max bok 1920px), wygenerowanie SEO ALT tagów opartych na tekście artykułu.
  5. **Podgląd w Telegramie:** Bot wysyła kandydata z miniaturami wybranych 4 zdjęć do zatwierdzenia.

#### 2. Arkadiusz Bińczyk — Wieloadresowość i Formaty:
- **Specyfika:** Wiadomości przychodzą z co najmniej 3 różnych skrzynek mailowych autora (WP, Interia, domena zawodowa).
- **Identyfikacja:** Połączenie dopasowania adresu nadawcy `From:` z wyszukiwaniem frazy *"Arkadiusz Bińczyk"* w podpisie maila oraz w metadanych plików `.docx` (pole *Author*).
- **Ekstrakcja:** Wyodrębnienie tekstu głównego z pominięciem nagłówków mailowych, przygotowanie pod format publicystyczny z mocnym leadem.

---

## 6. Schemat Danych Kandydata (Candidate Payload)

Każdy kandydat pozyskany przez dowolny worker ingestu zapisywany jest w zunifikowanym formacie JSON w bazie zadań:

```json
{
  "candidate_id": "cand_20260831_uokik_001",
  "source_type": "uokik_scraper",
  "source_name": "UOKiK Oficjalny",
  "target_portal": "kurier365",
  "priority": "P0",
  "created_at": "2026-08-31T14:30:00Z",
  "scheduled_for": "2026-08-31T14:30:00Z",
  "status": "pending_editorial_review",
  "content": {
    "title_raw": "Kara 14 mln zł dla operatora za bezprawne usługi",
    "lead_raw": "Prezes UOKiK wydał decyzję nakładającą karę na spółkę...",
    "body_raw": "Pełna treść komunikatu urzędowego...",
    "source_url": "https://uokik.gov.pl/aktualnosci/komunikat-1042",
    "attachments": [],
    "author": "UOKiK",
    "suggested_category": "Prawo & Konsument",
    "suggested_format": "news_alert"
  },
  "editorial": {
    "resume": "Prezes UOKiK ukarał operatora telekomunikacyjnego za aktywację płatnych usług bez zgody. Zwrot środków dla 250 tys. klientów.",
    "eco_bias_score": 0,
    "discover_potential_score": 95,
    "custom_instructions": null,
    "reviewed_by": null,
    "reviewed_at": null
  }
}
```

---

## 7. Rekomendowana Kolejność Wdrożenia (Faza 2 Roadmapy)

Aby jak najszybciej uruchomić produkcję, wdrażamy komponenty w 3 kolejnych sprintach:

### 🚀 TOP 3 Workery do Zbudowania w Pierwszej Kolejności:
1. **`gmail-kurier365-worker`** — kluczowy worker ingestu dla Kurier365.pl (obsługa skrzynki `tobroz@gmail.com`, whitelist nadawców: Rudiński z photo-curatorem, Bińczyk, WEI, Biały Kruk).
2. **`redaktor-naczelny-bot` (Telegram)** — serce orkiestracji i jedyny wymagany interfejs ludzki (prezentacja kandydatów z linkami i przyciskami Akceptuj / Odrzuć / Odrocz / Uwagi).
3. **`feed-crawler-worker` (Nauka, UOKiK, ISBNews)** — automatyzacja zbierania depesz krytycznych dla Kurier365 (UOKiK, Nauka) oraz BiznesCiti (ISBNews).

*(Następny krok po uruchomieniu TOP 3: `newseria-connector` z filtrem Eco-Bias oraz `biznesciti-worker`).*

---

[media-analyst-editorial | media-dispatch 31.08.2026] — specyfikacja kompletna
