# Raport Analityczny: Analiza Konstytucji VSE Workera, Błędów i Niedomówień (Sesja 22.09.2026)

- **Callsign:** `media-analyst`
- **Data:** 22.09.2026
- **Workspace:** `media-dispatch` / `sonic-void`
- **Status:** Raport kompletny

---

## 1. Stan aktualnej konstytucji (co już jest, co brakuje)

Aktualna wersja konstytucji (`.agents/knowledge/vse-worker-constitution.md`) nosi sygnaturę aktualizacji z 22.09.2026 (`media-dev-39`). Dokument stanowi fundament wiedzy operacyjnej dla workerów VSE, lecz dynamiczny przebieg sesji produkcyjnej z 21-22.09.2026 ujawnił szereg krytycznych braków, rozbieżności oraz nieudokumentowanych zachowań systemowych.

### Co już znajduje się w konstytucji:
1. **Środowisko i infrastruktura (Sekcja 1):** Prawidłowy port API (**8085**), nazwy kontenerów Docker (`vse-api`, `vse-postgres`, `vse-web`), namiary na VPS oraz bazę danych (`user=vse, db=vse`).
2. **Uwierzytelnianie JWT (Sekcja 2):** Niezawodny wzorzec generowania tokenu przez `jose.jwt.encode()` w kontenerze `vse-api` dla konta administratora `tobroz@gmail.com` (`sub: 4b97ab0c-98ee-46c6-9be8-d86adc4cb38a`).
3. **Status `/v1/youtube/publish-description` (Sekcja 3 i 14):** Oznaczenie endpointu jako uszkodzonego (`BROKEN`) dla kanałów Prawy.
4. **Wzorzec YouTube snippet update (Sekcja 14):** Zasada pobierania `youtube_description_body` z odpowiedzi live `POST /v1/generate` (brak pola w DB `transcript_jobs`), wymóg pobrania pełnego snippetu przez `videos().list()` przed `videos().update()` (brakujące `title` powodowało błąd 400), budowa skryptu kontenera jako lista linii bez zagnieżdżonych f-stringów.
5. **Autoryzacja kanałów YouTube (Sekcja 6 i 17):** Definicja aktywnych kanałów (`Studio Prawy_PL` oraz `Prawy TV`) i jawne wykluczenie kanałów out-of-scope (`Tomasz Brzozowski`, `VeriNarrMundo`).
6. **Architektura Shorts candidates → render (Sekcja 11):** Zastąpienie przestarzałego endpointu `/v1/shorts/generate` (422) nowym procesem `POST /v1/shorts/candidates` oraz `POST /v1/shorts/render`.

### Czego brakuje w konstytucji (luki ujawnione w sesji 22.09.2026):
1. **Brak dokumentacji endpointu `/v1/shorts/generate-srt/{yt_id}`:**
   - Konstytucja nie wspomina o konieczności wygenerowania pakietu napisów SRT przed zleceniem renderu.
   - Brak ostrzeżenia o błędzie **HTTP 429 Too Many Requests** ("Limit free: 2 filmy/miesiąc") dla konta agency/admin, co skutkowało traktowaniem tego błędu jako blokera zamiast ignorowania go i kontynuacji.
2. **Kolejność operacji w pipeline Shorts:**
   - Nie zdefiniowano ścisłego łańcucha: `(1) generate-srt` → `(2) candidates` → `(3) render`. Brak tej sekwencji skutkował renderowaniem shortów bez napisów.
3. **Obsługa ścieżek Windows i kodowania `local_overrides.json`:**
   - Brak ostrzeżenia przed raw stringami `r"...\u0142..."` w Pythonie, które zapisują literalne sekwencje znaków zamiast polskich liter i tworzą błędne puste katalogi w `C:\VSE\Shorts\`.
   - Brak wytycznej definiującej plik `AMEEncodingLog.txt` w kodowaniu `UTF-16LE` jako jedynego pewnego źródła lokalnych ścieżek wyjściowych MP4.
   - Brak wymogu `ensure_ascii=False` przy serializacji JSON do `local_overrides.json`.
4. **Kontrakt wejściowy `POST /v1/generate`:**
   - Brak wyraźnego ostrzeżenia, że polem adresu URL jest `video_url`, a nie `youtube_url` (błąd 422 przy pomyłce).
5. **Rygor pobierania opisów YouTube z silnika VSE:**
   - Brak jednoznacznego zakazu generowania własnych opisów przez subagentów AI i wymuszenia pobierania `youtube_description_body` i `post_title` wyłącznie z live response `/v1/generate`.
6. **Logika dopasowywania plików z AME logu:**
   - Brak ostrzeżenia przed naiwnym wyborem najkrótszej ścieżki (`min(..., key=len)`), co doprowadziło do pomylenia pliku roboczego `Rozbiory.mp4` z docelową wersją montażową `Rozbiory_2..mp4`.

---

## 2. Wszystkie bugi z opisem i rozwiązaniem (B1 – B8)

### B1 — local_overrides.json encoding & raw string Unicode escapes
- **Objaw:** W katalogu `C:\VSE\Shorts\` powstawały puste foldery z prefiksami `u0144ski...`, `u0142akowska...`, `u0105d_...`, a VSE Local Runner nie mógł odnaleźć plików źródłowych MP4 na dysku.
- **Root Cause:** W konfiguracji pipeline'u Python zdefiniowano ścieżki jako raw stringi:
  `r"C:\Users\tomas2\Videos\Prawy\P\u0142u\u017ca\u0144ski Ko\u0142akowska Danuta.mp4"`
  W raw-stringu (`r"..."`) sekwencja `\u0142` NIE jest konwertowana do litery `ł`, lecz staje się sześcioma znakami ASCII: `\`, `u`, `0`, `1`, `4`, `2`. Po rozdzieleniu ścieżki po ukośnikach fragment `\u0142akowska` stał się literalną nazwą podkatalogu.
- **Fix:**
  1. Całkowity zakaz ręcznego hardkodowania ścieżek z sekwencjami `\uXXXX`.
  2. Ścieżki należy ZAWSZE dynamicznie odczytywać z pliku logu Adobe Media Encoder:
     `C:\Users\tomas2\Documents\Adobe\Adobe Media Encoder\26.0\AMEEncodingLog.txt`
     otwieranego w kodowaniu `utf-16-le`.
  3. Zapis `local_overrides.json` musi odbywać się przez `open(..., 'w', encoding='utf-8')` z flagą `json.dump(..., ensure_ascii=False, indent=2)`.

### B2 — generate-srt rate limit HTTP 429
- **Objaw:** Wywołanie `POST /v1/shorts/generate-srt/{yt_id}?portal_id={portal_id}` zwracało status HTTP 429 z komunikatem: `"Limit free: 2 filmy/miesiąc"`.
- **Root Cause:** Błąd implementacji w logice sprawdzania planów subskrypcyjnych w backendzie VSE. Konto serwisowe `tobroz@gmail.com` posiada w tabeli `users` wartość `plan_id='agency'` oraz `is_admin=true`, jednak moduł weryfikacji limitów dla endpointu `generate-srt` traktował sesję jak plan Free lub nie uwzględniał uprawnień administratora.
- **Fix:**
  - *Doraźny (dla workerów):* Odnotować błąd 429 w logach, ale traktować jako błąd nieblokujący (`non-blocking warning`) i kontynuować pipeline.
  - *Docelowy:* Zgłosić task naprawczy do zespołu backendu VSE (`media-dev`) celem poprawy weryfikacji flagi `is_admin` oraz planu `agency` w dekoratorach limitów dla `generate-srt`.
  - *Wymóg operacyjny:* Endpoint ten MUSI być wywołany PRZED kolejkowaniem renderu (`/v1/shorts/render`), ponieważ Local Runner odpytuje o wygenerowany pakiet napisów (`short_srt_packages`).

### B3 — Brak napisów SRT przy generowanych Shortach
- **Objaw:** Wyrenderowane przez Local Runnera shorty wideo w formacie 9:16 nie posiadały wtopionych napisów (brak napisów drastycznie degraduje oglądalność na YouTube Shorts i TikTok).
- **Root Cause:** Odwrócona kolejność operacji w skryptach workerów: najpierw wywoływano `candidates`, natychmiast zlecano `render`, a `generate-srt` było pomijane lub uruchamiane po fakcie. Gdy Local Runner przetwarzał zlecenie renderu, pakiet SRT nie istniał w bazie danych VSE (`short_srt_packages`).
- **Fix:** Ustanowienie bezwzględnej sekwencji kroków:
  1. `POST /v1/shorts/generate-srt/{yt_id}` (generacja transkrypcji SRT na serwerze)
  2. `POST /v1/shorts/candidates` (wyznaczenie segmentów)
  3. `POST /v1/shorts/render` (zlecenie renderingu do Local Runnera)

### B4 — Błąd walidacji 422: pole `video_url` vs `youtube_url`
- **Objaw:** Wywołanie `POST /v1/generate` zwracało HTTP 422 Unprocessable Entity (`Field required: video_url`).
- **Root Cause:** Wiele endpointów w VSE (np. `/v1/shorts/candidates` czy dawny `/v1/shorts/generate`) używa klucza `youtube_url` lub `youtube_id`. W `POST /v1/generate` modelem wejściowym jest `GenerateRequest`, który oczekuje pola o nazwie `video_url`.
- **Fix:** W payloadzie dla `POST /v1/generate` zawsze stosować `video_url`:
  ```json
  {
    "video_url": "https://www.youtube.com/watch?v=...",
    "publication_type": "full_analysis",
    "portal_id": "2b047d7d-15a1-4d2f-8463-f89c2275bb73",
    "post_title": "...",
    "lang": "pl",
    "llm_provider": "claude"
  }
  ```

### B5 — Worker generował własne opisy YouTube zamiast brać z VSE
- **Objaw:** Opisy publikowane na YouTube odbiegały od standardów redakcyjnych Prawy.pl, brakowało sformatowanych rozdziałów ze znacznikami czasu, zoptymalizowanych hashtagów oraz linku zwrotnego do artykułu na portalu.
- **Root Cause:** Subagenci-workery próbowali samodzielnie konstruować opisy lub wywoływać dodatkowe prompty LLM, zamiast wykorzystać gotowy, przetestowany generator treści VSE. Ponadto szukali pola opisu w bazie PostgreSQL w tabeli `transcript_jobs`, gdzie pole to NIE jest zapisywane.
- **Fix:**
  - Całkowity zakaz generowania opisów przez workera na własną rękę.
  - ZAWSZE przechwytywać dane z odpowiedzi na żywo (`live response`) zapytania `POST /v1/generate`:
    - `post_title` / `seo_title` → Tytuł filmu (max 100 znaków).
    - `youtube_description_body` → Kompletny opis filmu.
    - Jeśli dodawany jest link do WP: dopisać na końcu `Czytaj wiecej: https://prawy.pl/?p={wp_post_id}`.

### B6 — Uszkodzony endpoint `/v1/youtube/publish-description`
- **Objaw:** Endpoint `POST /v1/youtube/publish-description` zwracał kod 400/403: `"channel not found or access denied"` dla filmów na kanałach Prawy.
- **Root Cause:** Problem w wewnętrznym routing'u i zarządzaniu sesjami OAuth w API VSE przy wywołaniach bezpośrednich.
- **Fix:** Publikacja tytułu i opisu przez dedykowany skrypt uruchamiany w kontenerze `vse-api`:
  1. Połączenie SSH z VPS i kontenerem `vse-api`.
  2. Załadowanie poświadczeń kanału z bazy `YouTubeChannel` i wywołanie `creds = _build_credentials(ch); creds.refresh(Request())`.
  3. Pobranie aktualnego snippetu przez `youtube.videos().list(part='snippet', id=video_id)`.
  4. Podmiana `snippet['title']` i `snippet['description']`.
  5. Aktualizacja pełnym snippetem przez `youtube.videos().update(part='snippet', body={'id': video_id, 'snippet': snippet})`.

### B7 — Próby publikacji na nieaktywnych kanałach YouTube
- **Objaw:** Skrypt aktualizujący opisy crashował lub raportował błędy autoryzacji przy kanałach `VeriNarrMundo` (`invalid_grant`) oraz `Tomasz Brzozowski`.
- **Root Cause:** Pętla po kanałach pobierała wszystkie aktywne kanały z bazy VSE, w tym konto prywatne oraz kanał z wygasłym tokenem OAuth.
- **Fix:** Sztywne filtrowanie identyfikatorów kanałów w kodzie dozwolonej białej listy:
  - `Studio Prawy_PL` (ID: `UCoH2G9By4OX3kcLsc8lHgDw`)
  - `Prawy TV` (ID: `UCNXh5eIlMVxnUBpTMKUp4CA`)
  Wszelkie inne identyfikatory muszą być pomijane instrukcją `continue`.

### B8 — Błędne dopasowanie plików w matcherze ścieżek: Rozbiory vs Rozbiory_2
- **Objaw:** Dla filmu Płużański Komuda Rozbiory 2 (`J0Z1xMSqkls`) matcher wybrał stary plik `Płużański Komuda Rozbiory.mp4` zamiast wyrenderowanego poprawnie `Płużański Komuda Rozbiory_2..mp4`.
- **Root Cause:** Matcher słów kluczowych `["komuda", "rozbiory"]` w przypadku znalezienia kilku pasujących plików stosował kryterium najkrótszej ścieżki: `min(matches, key=len)`. Plik bez sufiksu wersji `_2` był krótszy o 4 znaki, więc został błędnie wybrany jako dopasowanie.
- **Fix:**
  1. Parsowanie AME logu w porządku chronologicznym z priorytetem dla **ostatnich** (najnowszych) wystąpień pliku o danym temacie.
  2. Wykrywanie wariantów i sufiksów wersji montażowych (np. `_2`, `_final`, `_popr`).
  3. Precyzyjne słowa kluczowe w mapowaniu per wideo (np. `["komuda", "rozbiory", "2"]`).

---

## 3. Wszystkie niedomówienia do uzupełnienia w konstytucji (N1 – N5)

### N1: Kolejność operacji Shorts (generate-srt PRZED render)
- **Stan dotychczasowy:** Sekcja 11 konstytucji opisywała flow jako dwuetapowy: `candidates` → `render`. Brak wzmianki o `generate-srt`.
- **Uzupełnienie:** Sekcja 11 musi jednoznacznie określać trzykrokowy proces produkcji Shortów:
  1. `POST /v1/shorts/generate-srt/{yt_id}`
  2. `POST /v1/shorts/candidates`
  3. `POST /v1/shorts/render`
  Dopiero po wyrenderowaniu i uploadzie na YT wywoływany jest `POST /v1/shorts/describe`.

### N2: AME log jako jedyne źródło prawdy dla ścieżek lokalnych
- **Stan dotychczasowy:** Sekcja 16 wspominała o AME logu wyłącznie w kontekście nagrań biblijnych (`Select-String -Pattern "youtube.com"`).
- **Uzupełnienie:** Dla wszystkich programów (Płużański, Szafarowicz, Biblia, publicystyka) AME log (`C:\Users\tomas2\Documents\Adobe\Adobe Media Encoder\26.0\AMEEncodingLog.txt`) jest jedynym autorytatywnym źródłem ścieżek plików MP4. Plik MUSI być czytany z kodowaniem `utf-16-le`. Zakazane jest zgadywanie ścieżek i listowanie losowych katalogów.

### N3: Pole `video_url` w `POST /v1/generate` (nie `youtube_url`)
- **Stan dotychczasowy:** Sekcja 3 wymieniała endpointy bez specyfikacji nazw kluczy JSON. W sekcji 9 podano poprawny przykład, ale bez ostrzeżenia o pułapce.
- **Uzupełnienie:** Dodanie pułapki do tabeli sekcji 8 z wyraźnym zaznaczeniem: `POST /v1/generate` wymaga klucza `video_url`. Podanie `youtube_url` powoduje HTTP 422.

### N4: Błąd HTTP 429 na `generate-srt` = bug VSE, kontynuować pracę
- **Stan dotychczasowy:** Brak wzmianki w konstytucji. Każdy kod 4xx był traktowany przez nowych workerów jako awaria krytyczna przerywająca pipeline.
- **Uzupełnienie:** Odnotowanie w sekcji 8 i 11, że HTTP 429 z komunikatem o limicie planu free na `generate-srt` dla konta `tobroz@gmail.com` jest znanym defektem backendu VSE. Worker musi zalogować warning i niezwłocznie przejść do kolejnych etapów (`candidates` i `render`).

### N5: `local_overrides.json` zawsze z `ensure_ascii=False`
- **Stan dotychczasowy:** Konstytucja wskazywała ścieżkę pliku `C:\ProgramData\VSELocalRunner\local_overrides.json`, ale nie precyzowała reguł serializacji.
- **Uzupełnienie:** Zapis do pliku musi bezwzględnie używać `json.dump(overrides, f, ensure_ascii=False, indent=2)` z kodowaniem pliku UTF-8. Pominięcie tej flagi powoduje ucieczkę polskich znaków do `\uXXXX`, co uszkadza ścieżki i prowadzi do błędu B1.

---

## 4. Gotowe fragmenty kodu i tekstu do wklejenia do konstytucji

Poniższe fragmenty są gotowe do bezpośredniego scalenia z `.agents/knowledge/vse-worker-constitution.md`.

### Fragment A: Nowe pozycje do Sekcji 8 (Tabela Znanych Pułapek)

```markdown
| 22 | **`POST /v1/generate` pole `video_url`** | Kluczem w JSON jest `video_url`, a NIE `youtube_url`. Błędna nazwa daje HTTP 422. |
| 23 | **Kolejność Shortów: `generate-srt` PRZED `render`** | Local Runner potrzebuje pakietu SRT przy montażu. Sekwencja: (1) `generate-srt` -> (2) `candidates` -> (3) `render`. |
| 24 | **HTTP 429 na `generate-srt` = bug VSE (nie bloker)** | Backend VSE błędnie zgłasza limit free dla konta admin agency. Zaloguj ostrzeżenie i kontynuuj pipeline. |
| 25 | **Zapis `local_overrides.json` wymaga `ensure_ascii=False`** | Użycie domyślnego `ensure_ascii=True` lub raw stringów `r"...\u0142..."` niszczy polskie litery i tworzy błędne foldery. |
| 26 | **Naiwny matcher AME (`min(..., key=len)`) psuje wersjonowanie** | Wybiera np. `Rozbiory.mp4` zamiast `Rozbiory_2..mp4`. Czytaj AME log od końca (najnowsze eksporty). |
```

---

### Fragment B: Aktualizacja Sekcji 11 (Short Machine — Full Generation Pipeline)

```markdown
## 11. Short Machine — Full Generation Pipeline (Flow: generate-srt → candidates → render → describe)

> ⚠️ UWAGA: Pełny proces generowania shortów składa się z 4 kroków w ścisłej kolejności. Naruszenie kolejności skutkuje shortami bez napisów!

### Krok 1: Wygenerowanie pakietu SRT (PRZED renderem!)
```http
POST /v1/shorts/generate-srt/{yt_id}?portal_id=2b047d7d-15a1-4d2f-8463-f89c2275bb73
Headers: Authorization: Bearer {token}
```
> ⚠️ **Znany bug VSE:** Endpoint może zwrócić HTTP 429 ("Limit free: 2 filmy/miesiąc") mimo konta agency/admin. **NIE przerywaj pipeline'u** — zaloguj ostrzeżenie i przejdź do Kroku 2.

### Krok 2: Wyłonienie kandydatów na Shorty
```http
POST /v1/shorts/candidates
Headers: Authorization: Bearer {token}, Content-Type: application/json
```
Payload:
```json
{
  "youtube_id": "{yt_id}",
  "youtube_url": "https://www.youtube.com/watch?v={yt_id}",
  "count_emotional": 5,
  "count_professional": 5,
  "provider": "claude",
  "portal_id": "2b047d7d-15a1-4d2f-8463-f89c2275bb73"
}
```

### Krok 3: Renderowanie wyselekcjonowanych segmentów
```http
POST /v1/shorts/render
Headers: Authorization: Bearer {token}, Content-Type: application/json
```
Payload per candidate:
```json
{
  "youtube_id": "{yt_id}",
  "youtube_url": "https://www.youtube.com/watch?v={yt_id}",
  "local_path": "{dokladna_sciezka_z_ame_logu}",
  "start_sec": 120.0,
  "end_sec": 165.0,
  "candidate_data": { "optimized_title": "..." },
  "render_format": "9:16",
  "output_dir": "C:\\VSE\\Shorts",
  "portal_id": "2b047d7d-15a1-4d2f-8463-f89c2275bb73"
}
```

### Krok 4: Optymalizacja SEO po uploadzie na YouTube
Po wyrenderowaniu i opublikowaniu materiału na kanale YT, wywołaj:
```http
POST /v1/shorts/describe
```
```

---

### Fragment C: Moduł Rozwiązywania Ścieżek z AME Logu i Aktualizacji Overrides (Python)

```python
import re
import os
import json

AME_LOG_PATH = r"C:\Users\tomas2\Documents\Adobe\Adobe Media Encoder\26.0\AMEEncodingLog.txt"
LOCAL_OVERRIDES_PATH = r"C:\ProgramData\VSELocalRunner\local_overrides.json"

def resolve_ame_local_paths(film_keywords_map):
    """
    Czyta AME log w kodowaniu UTF-16LE.
    Dopasowuje unikalne pliki MP4 do filmów unikając pułapki najkrótszej nazwy (Rozbiory vs Rozbiory_2).
    """
    if not os.path.exists(AME_LOG_PATH):
        raise FileNotFoundError(f"Brak pliku logu AME: {AME_LOG_PATH}")

    with open(AME_LOG_PATH, "r", encoding="utf-16-le", errors="replace") as f:
        content = f.read()

    pattern = r"[A-Za-z]:\\[^\n\r\t\"]+?\.mp4"
    all_paths = re.findall(pattern, content, re.IGNORECASE)
    
    # Filtruj ścieżki do folderu Prawy/Videos i usuń duplikaty zachowując kolejność
    prawy_paths = list(dict.fromkeys(p for p in all_paths if "Prawy" in p and "Videos" in p))

    resolved = {}
    for yt_id, keywords in film_keywords_map.items():
        # Szukaj dopasowań zawierających wszystkie słowa kluczowe
        matches = [p for p in prawy_paths if all(k.lower() in p.lower() for k in keywords)]
        if not matches:
            print(f"[AME-WARN] Brak dopasowania dla {yt_id} ({keywords})")
            continue
        
        # Wybieramy OSTATNI wyrenderowany plik (najnowszy z logu AME) zamiast min(..., key=len)
        chosen = matches[-1]
        if os.path.exists(chosen):
            resolved[yt_id] = chosen
            print(f"[AME-OK] {yt_id} -> {chosen}")
        else:
            print(f"[AME-ERR] Plik nie istnieje na dysku: {chosen}")

    return resolved

def update_local_overrides_safe(overrides_dict):
    """Bezpieczny zapis mapowania z wymuszeniem UTF-8 i ensure_ascii=False."""
    existing = {}
    if os.path.exists(LOCAL_OVERRIDES_PATH):
        try:
            with open(LOCAL_OVERRIDES_PATH, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = {}

    existing.update(overrides_dict)
    os.makedirs(os.path.dirname(LOCAL_OVERRIDES_PATH), exist_ok=True)
    with open(LOCAL_OVERRIDES_PATH, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    print(f"[OVERRIDES] Zaktualizowano {len(overrides_dict)} wpisów w local_overrides.json")
```

---

*Raport sporządził: `media-analyst` | media-dispatch | 22.09.2026*
