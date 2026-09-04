---
name: pressai-orchestrator
description: >-
  Orchestrator wsadu do PressAI. Łączy narzędzia Content Radar (URL/Mail) z backendem PressAI. 
  Odpowiada za pobranie treści, interakcję z użytkownikiem (wybór fraz SEO) oraz generację i planowanie artykułów.
---

# PressAI Input Orchestrator (media-dispatch)

Ten skill definiuje wieloetapowy proces (Runbook) przetwarzania surowego wsadu (URL lub Mail z Content Radar) na gotowy, zaplanowany artykuł w PressAI. 

Zawsze postępuj zgodnie z poniższymi krokami, aby nie ominąć logiki SEO. Do komunikacji z API używaj narzędzi HTTP (np. curl lub pythona).

## Zmienne środowiskowe i endpointy
* Bazowy URL PressAI: `https://press.impresjapr.pl/api` (zmień na lokalny host, jeśli pracujesz w środowisku dev).
* Upewnij się, że posiadasz token autoryzacji do tych endpointów (w zależności od reguł workspace).

---

## KROK 1: Pobranie źródła (Source Extraction)
Na podstawie tego, co przekaże Ci Content Radar, wybierz jedną ze ścieżek:

### Ścieżka A: URL ze strony internetowej
1. Wykonaj: `POST /extract`
2. Payload: `{"url": "<ADRES_URL>"}`
3. Zapisz w pamięci: `source_text` z odpowiedzi.

### Ścieżka B: E-mail (Gmail)
1. Wykonaj: `POST /prepare-article`
2. Parametry (body/query): `message_id` oraz `account_id`.
3. Zapisz w pamięci: `source_text` oraz tablicę `images` (jeśli maile miały załączniki).

---

## KROK 2: Analiza SEO i przygotowanie fraz
Musisz pobrać rekomendacje dla pobranego tekstu.
1. Wykonaj: `POST /phrase-candidates`
2. Payload: `{"source_text": "<source_text z kroku 1>", "target_portal": "<nazwa_portalu>"}`
3. Zapisz w pamięci: Zwróconą tablicę kandydatów na frazy (zazwyczaj obiekty `{"phrase": "..."}`).

---

## KROK 3: Interakcja z Człowiekiem (Human-in-the-Loop) - KRYTYCZNE!
Bezwzględnie użyj narzędzia `ask_question`, aby zablokować proces i poprosić usera o decyzję.
**NIGDY NIE ZGADUJ FRAZY GŁÓWNEJ!**

Skonfiguruj zapytanie `ask_question` następująco:
* Pytanie 1: "Wybierz Główną Frazę SEO (lub wpisz własną)" -> `is_multi_select: false`. Opcje: wyciągnięte frazy z kroku 2.
* Pytanie 2: "Wybierz Frazy Poboczne (opcjonalnie)" -> `is_multi_select: true`. Opcje: te same co wyżej.
* Pytanie 3: "Czy tekst ma być IN EXTENSO (przedruk 1:1)?" -> Opcje: ["Tak", "Nie"].
* Pytanie 4: "Wybierz Format Dziennikarski" -> (możesz pobrać wcześniej opcje z `GET /formats`).

Zapisz odpowiedzi użytkownika. Jeśli wskazał frazy poboczne, sformatuj je w ciąg tekstowy (np. "Frazy poboczne: fraza1, fraza2").

---

## KROK 4: Generacja Artykułu
Zbuduj ostateczny payload i wyślij go do silnika AI.
1. Wykonaj: `POST /generate`
2. Payload (przykład):
```json
{
  "source_text": "<tekst_z_kroku_1>",
  "target_portal": "<wybrany_portal>",
  "selected_phrase": "<FRAZA_GŁÓWNA_Z_KROKU_3>",
  "seo_context": "Dodatkowe frazy poboczne (uwzględnij naturalnie w tekście): <FRAZY_POBOCZNE_Z_KROKU_3>",
  "formats": ["<FORMAT_Z_KROKU_3>"],
  "generate_faq": true,
  "is_in_extenso": <TRUE_CZY_FALSE_Z_KROKU_3>,
  "image_metadata": <TABLICA_IMAGES_Z_KROKU_1B_LUB_PUSTA>
}
```
Zaczekaj na wygenerowanie i zapisanie artykułu w systemie PressAI (ID artykułu).

---

## KROK 5: Przegląd i Harmonogram Publikacji
Poproś użytkownika o przejrzenie wygenerowanego artykułu w interfejsie PressAI (podaj mu link lub ID).
Zapytaj go (kolejne `ask_question` lub zwykły tekst), czy chce artykuł opublikować teraz, zaplanować na przyszłość, czy zostawić jako Draft.

Jeśli użytkownik poda datę w przyszłości (np. "Jutro o 15:00"):
1. Przekonwertuj datę na ISO8601 (np. `2026-09-05T15:00:00`).
2. Wykonaj publikację: `POST /publish` (lub równoważny endpoint).
3. Payload:
```json
{
  "portal_id": <ID_PORTALU>,
  "status": "future",
  "publish_date": "<DATA_ISO8601>"
}
```
Backend PressAI natywnie obsłuży zaplanowanie wpisu na WordPressie bez potrzeby ustawiania lokalnego przypomnienia/crona.
