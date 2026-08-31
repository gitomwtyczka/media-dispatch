# Raport: Specyfikacja Źródeł i Flow Redakcyjnego (Kurier365.pl & BiznesCiti.com)

**Autor:** `[media-analyst-editorial | media-dispatch 31.08.2026]`  
**Do:** Supervisor 01 / Redaktor Naczelny  
**Workspace:** `media-dispatch`  
**Dotyczy:** Wdrożenie codziennej produkcji artykułów dla portali `kurier365.pl` i `biznesciti.com`  
**Dokument główny:** `media-dispatch/docs/editorial-sources-spec.md`  

---

## 1. Podsumowanie Wykonanej Pracy

Zgodnie z briefem użytkownika opracowano pełną specyfikację źródeł, architekturę dedykowanych workerów ingestu oraz flow decyzyjny Redaktora Naczelnego AI.

### Kluczowe Elementy Specyfikacji:

1. **Kurier365.pl (Źródła i Routing):**
   - **Gmail (`tobroz@gmail.com`):**
     - *Cezary Rudiński:* obsługa 2 adresów e-mail, dedykowany moduł `photo-curator` (selekcja 4–6 najlepszych zdjęć z paczek 8–30 załączników, konwersja WebP, opisy ALT).
     - *Arkadiusz Bińczyk:* reguły rozpoznawania 3 adresów nadawcy + fallback po sygnaturze i metadanych `.docx`.
     - *WEI (Warsaw Enterprise Institute):* filtrowanie domeny `@wei.org.pl`, adaptacja tez do formatu Discover.
     - *Biały Kruk:* materiały książkowo-kulturalne z domeny `@bialykruk.pl`.
   - **UOKiK:** Priorytet **P0 (Krytyczny)** — monitoring komunikatów urzędowych, decyzji i kar Prezesa UOKiK, automatyczne alerty konsumenckie.
   - **Dział NAUKA & Inne działy:** automatyczna agregacja RSS (feed crawler) z 30-minutowym interwałem.
   - **Newseria:** depesze lifestylowe, społeczne i innowacyjne.

2. **BiznesCiti.com (Źródła i Routing B2B):**
   - **ISBNews:** Priorytet **P0** — pierwotne źródło depesz giełdowych, makro i spółek.
   - **Zagrożenia wojenne i geopolityka:** monitorowanie surowców (ropa, gaz), łańcuchów dostaw i sankcji.
   - **Polskie i światowe portale biznesowe:** benchmarking (FT, Bloomberg, Reuters, Money, Bankier, CIRE).
   - **Daleki Wschód:** kadencja 2–3x/tydz. (Nikkei Asia, SCMP — technologie, półprzewodniki).
   - **Newseria Biznes:** wdrożenie **Eco-Bias & Neutrality Gate** (filtr AI eliminujący jednostronny eko-aktywizm i greenwashing na rzecz twardego rachunku ekonomicznego).

3. **Interfejs Redaktora Naczelnego (Kanał Wewnętrzny):**
   - **Rekomendacja:** **Telegram Bot (`redaktor-naczelny-bot`)**.
   - Powiadomienia push w czasie rzeczywistym z resume (250 zn) i bezpośrednim linkiem do źródła.
   - Przyciski inline: `[✅ Akceptuj]` `[❌ Odrzuć]` `[⏰ Odrocz D+1]` `[⏰ Odrocz D+7]` `[💬 Uwagi]`.
   - 1 kliknięcie `Akceptuj` uruchamia `pressai-worker` i w 45–60s tworzy gotowy wpis `draft` w WordPressie.

4. **Aktualizacja ROADMAP.md:**
   - Wdrożono wersję **ROADMAP v1.2** z nową **Fazą 2: Multi-portal Daily Production**.

---

## 2. TOP 3 Workery do Zbudowania (Kolejność Wdrożenia)

1. **`gmail-kurier365-worker`** — ingest mailowy dla Kurier365 (obsługa tobroz@gmail.com, Rudiński z photo-curatorem, Bińczyk, WEI, Biały Kruk).
2. **`redaktor-naczelny-bot` (Telegram)** — serce orkiestracji i interfejs decyzji redaktora (prezentacja kandydatów + akcje inline).
3. **`feed-crawler-worker` (Nauka, UOKiK, ISBNews)** — automatyczny monitoring RSS kluczowych działów merytorycznych.

---

[media-analyst-editorial | media-dispatch 31.08.2026] — raport kompletny
