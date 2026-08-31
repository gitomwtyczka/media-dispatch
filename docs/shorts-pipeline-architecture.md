# Architektura Shorts Pipeline — Studio Prawy_PL & media-dispatch

> **Autor**: `media-analyst` | **Data**: 2026-08-31 | **Workspace**: `media-dispatch`  
> **Status**: Specyfikacja Architektoniczna v1.0 | **Branch**: `main`

---

## 1. Wprowadzenie i Cel Biznesowy

Kanał **Studio Prawy_PL** (`UCoH2G9By4OX3kcLsc8lHgDw`) oraz portal **Prawy.pl** produkują codzienne materiały wideo (analizy polityczne, publicystykę, komentarze). Format długi (long-form wideo) jest fundamentem treści, jednak największy potencjał wiralowy oraz pozyskiwania nowych subskrybentów leży w formatach pionowych 9:16 (**YouTube Shorts** oraz **TikTok**).

Niniejszy dokument opisuje kompletną, 4-agentową architekturę **Shorts Pipeline**: od wykrycia filmu z gotowymi napisami na YouTube, przez generowanie surowych klipów w VSE i obróbkę redakcyjną na PC, aż po optymalizację SEO przez moduł **Short Machine**, harmonogramowanie i publikację na TikToku.

---

## 2. Diagram Przepływu (End-to-End Pipeline)

```mermaid
flowchart TD
    subgraph S1["1. Intelligence & Detection"]
        YTA["Agent 1: youtube-agent"]
        YT_CH["YouTube Studio Prawy_PL<br/>(Channel ID: UCoH2G9By4OX3kcLsc8lHgDw)"]
        YT_CH -->|1. Polling nowych filmów| YTA
        YTA -->|2. Weryfikacja gotowości ASR captions| YTA
    end

    subgraph S2["2. Core Engine & Rendering"]
        VSE["Agent 2: VSE (vse-worker)"]
        YTA -->|3. POST /v1/generate + /v1/inject| VSE
        WP["WordPress prawy.pl<br/>(Draft / Future + Rank Math)"]
        VSE -->|4. Artykuł + SEO Meta| WP
        VSE -->|5. POST /v1/shorts/candidates + render| VSE_RENDER["VSE Video Renderer"]
        FS_RAW["Lokalny Dysk PC:<br/>C:\\VSE\\Shorts\\[Film]_[date]\\[klip]_raw.mp4"]
        VSE_RENDER -->|6. Zapis surowych klipów 9:16| FS_RAW
    end

    subgraph S3["3. Editorial Touch & Quality Gate"]
        USER["Montażysta / Redaktor"]
        FS_RAW -->|7. Przegląd i dopracowanie klipu| USER
        FS_READY["Lokalny Dysk PC:<br/>C:\\VSE\\Shorts\\[Film]_[date]\\[klip]_gotowy.mp4"]
        USER -->|8. Zapis z sufiksem _gotowy.mp4| FS_READY
    end

    subgraph S4["4. Optimization & Scheduling"]
        SA["Agent 3: shorts-agent"]
        SM["Short Machine<br/>(VSE SEO Description Engine)"]
        YT_SHORTS["YouTube Shorts Channel"]
        
        SA -->|9. Skan opublikowanych shortów| YT_SHORTS
        SA -->|10. Wykrycie braku opisu SEO| SM
        SM -->|11. Wygenerowany opis, tagi, hashtagi| SA
        SA -->|12. YouTube Data API: update opisu| YT_SHORTS
        SA -->|13. Generowanie kalendarza publikacji| SCHED["shared/schedules/shorts_schedule.json"]
    end

    subgraph S5["5. Multi-Platform Distribution"]
        TT["Agent 4: tiktok-worker"]
        FS_READY -->|14. Odczyt gotowych klipów| TT
        SCHED -->|15. Zgodnie z harmonogramem| TT
        SM -.->|16. Pobranie copy/hashtagów| TT
        TT -->|17. Upload wideo| TIKTOK["Profil TikTok Prawy.pl"]
    end
```

---

## 3. Szczegółowy Opis 4 Agentów

| Agent | Typ / Status | Odpowiedzialność | Główne Wejścia (Input) | Główne Wyjścia (Output) |
|---|---|---|---|---|
| **Agent 1: `youtube-agent`** | Planowany (`media-dispatch`) | Monitorowanie kanału YT, gating gotowości transkrypcji (ASR), dispatch do VSE | YouTube Data API (`UCoH2G9By4OX3kcLsc8lHgDw`) | Taski przetwarzania dla VSE |
| **Agent 2: `vse-worker`** | Istniejący (`prawy-studio-worker`) | Generowanie artykułu WP, SEO, kandydatów shortów Claude, renderowanie wideo 9:16 | YouTube URL / Video ID, audio/wideo | Artykuł WP, zaktualizowany film YT, pliki `_raw.mp4` w `C:\VSE\Shorts\` |
| **Agent 3: `shorts-agent`** | Nowy (niniejsza specyfikacja) | Skanowanie opublikowanych shortów, generowanie opisów SEO (Short Machine), aktualizacja YT API, harmonogramowanie | Lista shortów YT, API Short Machine, konfiguracja slotów czasowych | Zaktualizowane opisy na YT, plik harmonogramu `shorts_schedule.json` |
| **Agent 4: `tiktok-worker`** | Planowany (Faza 5b) | Publikacja gotowych klipów pionowych na platformie TikTok | Pliki `*_gotowy.mp4`, metadane z Short Machine, harmonogram | Opublikowane wideo TikTok, logi publikacji |

---

### Agent 1: `youtube-agent` (Ingestion & Gating)
- **Rola**: Autonomiczny monitor kanału Studio Prawy_PL.
- **Działanie**:
  1. Cyklicznie (cron co 15–30 minut) sprawdza listę najnowszych wideo na kanale `UCoH2G9By4OX3kcLsc8lHgDw`.
  2. Sprawdza status napisów (Captions API). Jeśli napisy automatyczne (`ASR`) nie są jeszcze przeliczone przez YouTube — czeka i ponawia próbę w kolejnym cyklu (tzw. Captions Gating).
  3. Po potwierdzeniu gotowości napisów wywołuje pipeline w `vse-worker` lub bezpośrednio endpointy VSE.

---

### Agent 2: `vse-worker` (Core Generation & Video Rendering)
- **Rola**: Główny silnik produkcyjny VSE (Video SEO Engine).
- **Działanie**:
  1. `POST /v1/generate` (LLM Claude 3.5 Sonnet) $\rightarrow$ generuje artykuł na portal prawy.pl, lead, frazy kluczowe, FAQ, rozdziały.
  2. `POST /v1/inject` $\rightarrow$ wstrzykuje draft/future do WordPressa z miniaturą YT i metadanymi Rank Math.
  3. `PUT /v1/youtube/publish-description` $\rightarrow$ aktualizuje opis filmu na YouTube o rozdziały, linki i CTA.
  4. `POST /v1/shorts/candidates` $\rightarrow$ Claude analizuje transkrypt VTT i wskazuje 5–10 najciekawszych fragmentów (timecodes start/end, hook, score wiralowości).
  5. `POST /v1/shorts/render` $\rightarrow$ VSE renderuje surowe klipy wideo w formacie 9:16 i zapisuje je lokalnie.

---

### Agent 3: `shorts-agent` (SEO Optimization & Scheduling)
- **Rola**: Strażnik optymalizacji SEO dla formatu krótkiego oraz planista publikacji.
- **Działanie**:
  1. **Skanowanie YouTube**: Odpytuje YouTube Data API o opublikowane shorty na kanale Studio Prawy_PL.
  2. **Audyt Opisów**: Sprawdza, czy dany Short posiada pełny opis SEO wygenerowany przez Short Machine.
  3. **Wzbogacenie przez Short Machine**: Jeśli opis jest pusty lub szczątkowy $\rightarrow$ przesyła identyfikator shorta do Short Machine, pobiera zoptymalizowany pakiet SEO i aktualizuje wideo przez `videos.update`.
  4. **Harmonogramowanie**: Na podstawie bazy zidentyfikowanych surowych/gotowych klipów (~6 z jednego filmu głównego) wylicza optymalny kalendarz dystrybucji na kolejne dni i godziny.

---

### Agent 4: `tiktok-worker` (Multi-Platform Distribution)
- **Rola**: Eksporter gotowych klipów na profil TikTok.
- **Działanie**:
  1. Monitoruje katalogi `C:\VSE\Shorts\[Film]_[date]\` w poszukiwaniu plików oznaczonych sufiksem `*_gotowy.mp4`.
  2. Odczytuje metadane (tytuł, opis, hashtagi) zsynchronizowane przez Short Machine.
  3. Publikuje materiał na TikToku zgodnie z wyznaczonym slotem z pliku harmonogramu.

---

## 4. Struktura Katalogów na PC

Pliki wideo przetwarzane lokalnie w środowisku Windows posiadają ściśle zdefiniowaną strukturę katalogów oraz konwencję nazewnictwa plików:

```text
C:\VSE\Shorts\
  ├── [Nazwa_Filmu]_[YYYY-MM-DD]\          ← folder dedykowany per film bazowy
  │     ├── metadata.json                   ← metadane kandydatów z VSE (timecodes, hooki)
  │     ├── [klip_1]_raw.mp4               ← surowy klip 9:16 zrenderowany przez VSE
  │     ├── [klip_1]_gotowy.mp4            ← klip po montażu/akceptacji usera (GOTOWY DO PUBLIKACJI)
  │     ├── [klip_2]_raw.mp4
  │     ├── [klip_2]_gotowy.mp4
  │     ├── [klip_3]_raw.mp4
  │     └── [klip_3]_gotowy.mp4
  └── ...
```

### Zasady konwencji nazewniczej:
1. `_raw.mp4` — plik wyjściowy z automatycznego renderingu VSE. Zawiera wycięty kadr pionowy z nałożonymi napisami automatycznymi.
2. `_gotowy.mp4` — plik, który przeszedł przez weryfikację człowieka (montażysty/redaktora). Może zawierać poprawione kadrowanie, dodatkowe plansze lub poprawione literówki w napisach.
3. **Zasada bezpieczeństwa**: Agenty dystrybucyjne (`tiktok-worker`, uploadery) **nigdy nie publikują plików `_raw.mp4`**. Publikacji podlegają wyłącznie pliki posiadające w nazwie sufiks `_gotowy.mp4`.

---

## 5. Short Machine — Koncepcja i Specyfikacja API

### 5.1. Czym jest Short Machine?
**Short Machine** to dedykowany moduł optymalizacji SEO dla formatów pionowych (Shorts / Reels / TikTok). W przeciwieństwie do pełnego generatora artykułów VSE, Short Machine skupia się na:
- **Hooku** (pierwsze 3 sekundy uwagi widza),
- **Maksymalnie skondensowanym opisie** (zoptymalizowanym pod wyszukiwarkę Shorts i algorytm rekomendacji),
- **Precyzyjnym zestawie hashtagów** (#Shorts, tagi kanału, tagi tematyczne),
- **Przypiętym komentarzu (Pinned Comment CTA)** odsyłającym do pełnego filmu na YouTube lub artykułu na Prawy.pl.

### 5.2. Architektura i Endpointy API
Short Machine może działać jako endpoint w `vse-api` (na porcie `8085`) lub jako mikromoduł w `media-dispatch`.

#### Endpoint: `POST /v1/shorts/seo-description`
- **Request Body**:
```json
{
  "youtube_id": "abc123shortId",
  "parent_video_id": "xyz789longId",
  "short_title": "Tytuł roboczy klipu",
  "transcript_excerpt": "Tekst wypowiedzi w tym 45-sekundowym fragmencie...",
  "target_platform": "youtube_shorts",
  "lang": "pl"
}
```

- **Response Body**:
```json
{
  "status": "success",
  "seo_data": {
    "optimized_title": "Mocne słowa o podatkach! Czy Polacy zapłacą więcej? #Shorts",
    "description": "Gorąca dyskusja w Studio Prawy_PL. Zobacz kluczowy fragment rozmowy o nowych regulacjach.\n\n🔔 Subskrybuj kanał @StudioPrawy_PL aby nie przegapić nowych materiałów!\n\n#Shorts #PrawyPL #Polska #Gospodarka #Wiadomości",
    "hashtags": ["#Shorts", "#PrawyPL", "#Polska", "#Gospodarka", "#Wiadomości"],
    "tags": ["studio prawy pl", "prawy pl", "podatki", "gospodarka polska", "shorts"],
    "pinned_comment": "👉 Całą rozmowę obejrzysz tutaj: https://www.youtube.com/watch?v=xyz789longId\n📰 Przeczytaj artykuł na: https://prawy.pl"
  }
}
```

---

## 6. Harmonogram Publikacji Shortów (Scheduling Engine)

### 6.1. Matematyka i Zasady Rozkładu
- Z jednego filmu pełnometrażowego generowanych jest zazwyczaj **~6 klipów**.
- **Reguła anty-kanibalizacji**: Publikacja 6 shortów w ciągu jednej godziny drastycznie obniża zasięgi w algorytmie YouTube.
- **Strategia dystrybucji**:
  - Rozłożenie materiałów na **2 do 3 dni** (po 2–3 shorty dziennie), lub
  - Rozłożenie na **6 dni** (1 short dziennie, jako stały dopływ ruchu).

### 6.2. Okna Czasowe Najwyższego Zaangażowania (Peak Engagement Slots)
Dla kanałów publicystyczno-informacyjnych w Polsce zdefiniowano 4 kluczowe sloty:
1. **07:00 CEST** — Poranny przegląd wiadomości (dojazd do pracy/szkoły).
2. **12:00 CEST** — Przerwa obiadowa (krótka konsumpcja treści mobilnych).
3. **18:00 CEST** — Popołudniowy szczyt zaangażowania (powrót z pracy).
4. **21:00 CEST** — Wieczorny prime-time (relaks, wysoki watch-time).

### 6.3. Format Danych Harmonogramu (`shared/schedules/shorts_schedule.json`)

```json
{
  "generated_at": "2026-08-31T21:30:00+02:00",
  "parent_video_id": "dL8-MeQobrU",
  "parent_title": "Debata o przyszłości mediów w Polsce",
  "shorts_count": 6,
  "schedule": [
    {
      "short_index": 1,
      "clip_file_raw": "C:\\VSE\\Shorts\\Debata_2026-09-01\\klip_1_raw.mp4",
      "clip_file_ready": "C:\\VSE\\Shorts\\Debata_2026-09-01\\klip_1_gotowy.mp4",
      "youtube_short_id": "sh_111aaa",
      "planned_publish_time": "2026-09-01T07:00:00+02:00",
      "status": "scheduled",
      "platforms": ["youtube_shorts", "tiktok"],
      "seo": {
        "title": "Kluczowy moment debaty! #Shorts",
        "description": "Zobacz najostrzejszy fragment wymiany zdań...",
        "hashtags": ["#Shorts", "#PrawyPL", "#Media"]
      }
    },
    {
      "short_index": 2,
      "clip_file_raw": "C:\\VSE\\Shorts\\Debata_2026-09-01\\klip_2_raw.mp4",
      "clip_file_ready": "C:\\VSE\\Shorts\\Debata_2026-09-01\\klip_2_gotowy.mp4",
      "youtube_short_id": "sh_222bbb",
      "planned_publish_time": "2026-09-01T18:00:00+02:00",
      "status": "pending_manual_edit",
      "platforms": ["youtube_shorts", "tiktok"],
      "seo": {
        "title": "Co dalej z wolnością słowa? #Shorts",
        "description": "Mocny komentarz redakcji...",
        "hashtags": ["#Shorts", "#PrawyPL", "#Polska"]
      }
    }
  ]
}
```

---

## 7. Otwarte Pytania i Decyzje Architektoniczne (TODO)

1. **Model autoryzacji TikToka**: Czy `tiktok-worker` będzie korzystał z oficjalnego TikTok Content Posting API (wymaga konta deweloperskiego i weryfikacji aplikacji), czy z mechanizmu semi-automated (przygotowanie paczki w chmurze + notyfikacja)?
2. **Kto publikuje Shorty na YouTube**: Czy shorty są wgrywane na YouTube ręcznie przez zespół, a `shorts-agent` je tylko wykrywa i uzupełnia opisy, czy `shorts-agent` docelowo ma sam wrzucać pliki wideo na YouTube Data API (`videos.insert`)?
3. **Lokalizacja Short Machine**: Czy Short Machine ma być nowym endpointem w kontenerze `vse-api` (`/v1/shorts/seo-description`), czy osobnym mikroserwisem/modułem Python w repozytorium `media-dispatch`?

---

*[media-analyst | media-dispatch 31.08.2026] — specyfikacja architektury kompletna*
