# shorts-agent

Dedykowany agent zarządzający formatem krótkim (Shorts / Reels / TikTok) dla kanału **Studio Prawy_PL** w architekturze `media-dispatch`.
Odpowiada za audyt opublikowanych shortów, generowanie brakujących opisów SEO przez **Short Machine API** na produkcji, aktualizację YouTube Data API oraz harmonogramowanie dystrybucji.

---

## Co robi

1. **Skanuje kanał YouTube Studio Prawy_PL** (`UCoH2G9By4OX3kcLsc8lHgDw`) pod kątem opublikowanych filmów typu Short.
2. **Weryfikuje jakość SEO opisu każdego shorta** (audyt opisu Short Machine):
   - Sprawdza czy Short posiada pełny opis wygenerowany przez Short Machine (`description.length < 50` lub tytuł = nazwa pliku `.mp4` $\rightarrow$ traktuj jako brak opisu SM).
   - Przekazuje `youtube_id` do **Short Machine** (`POST /v1/shorts/describe`).
   - Aktualizuje tytuł (front-loaded max 45 zn, bez `#Shorts`), zoptymalizowany opis (150–350 zn, bez URL), tagi i przypięty komentarz na YouTube przez YouTube Data API v3.
3. **Planuje harmonogram publikacji (Scheduling Engine)**:
   - Grupuje surowe/gotowe klipy (~6 z jednego filmu głównego z `C:\VSE\Shorts\[Film]_[date]\`).
   - Rozkłada publikacje w czasie na 2–6 dni.
   - Dopasowuje publikacje do okien szczytowej oglądalności (`07:00`, `12:00`, `18:00`, `21:00 CEST`).
   - Generuje wyjściowy plik `shared/schedules/shorts_schedule.json`.
4. **Wspiera dystrybucję TikTok (Faza 5b)**:
   - Integruje się z `tiktok-worker` i przekazuje gotowe pliki `*_gotowy.mp4` wraz z opisami SEO do publikacji na profilu TikTok.

---

## Integracja Short Machine

Moduł **Short Machine** jest wdrożony i aktywny na środowisku produkcyjnym VSE od **31.08.2026**.

### 1. Endpoint & Autoryzacja
- **Endpoint**: `POST https://vse.impresjapr.pl/v1/shorts/describe` (lub wewnątrz sieci VPS: `http://localhost:8085/v1/shorts/describe`)
- **Autoryzacja**: Bearer JWT token (taki sam jak dla całego VSE API)

### 2. Format Wejścia (Input)
```json
{
  "youtube_id": "ABC123defGH",
  "portal_id": "2b047d7d-15a1-4d2f-8463-f89c2275bb73"
}
```

### 3. Format Wyjścia (Output)
```json
{
  "optimized_title": "Mocne słowa o podatkach! Zapłacimy więcej?",
  "description": "Gorąca dyskusja w Studio Prawy_PL o nowych regulacjach podatkowych i ich skutkach dla Polaków.\n\n🔔 Subskrybuj @StudioPrawy_PL!\n\n#PrawyPL #Podatki #Gospodarka #Polska #Wiadomości",
  "hashtags": ["#PrawyPL", "#Podatki", "#Gospodarka", "#Polska", "#Wiadomości"],
  "pinned_comment": "💬 Czy Twoim zdaniem nowe regulacje uderzą w Twój portfel? Napisz poniżej! 👇\n\n🎥 Całą rozmowę znajdziesz w powiązanym filmie!",
  "related_video_id": "xyz789longId"
}
```

### 4. Przepływ Przetwarzania (Flow)
```text
1. Listuj YT Shorts (YouTube Data API: playlistItems / search)
       │
       ▼
2. Sprawdź czy Short ma opis Short Machine:
   - Czy description.length < 50?
   - Czy title == nazwa pliku mp4 (np. "klip_1_gotowy.mp4")?
   - Czy brak hashtagów / brak spójnego CTA?
       │
       ├─► [TAK: ma opis SM] ──► Pomiń (lub raportuj status OK)
       │
       ▼ [NIE: brak opisu SM]
3. Wywołaj POST /v1/shorts/describe z youtube_id i portal_id
       │
       ▼
4. Aktualizuj YouTube Data API:
   - videos.update (snippet.title = optimized_title, snippet.description = description)
   - commentThreads.insert (wstawienie pinned_comment z konta kanału i przypięcie)
   - Ustawienie Powiązanego Filmu (related_video_id) w YouTube Studio
```

### 5. Krytyczne Reguły Algorytmiczne i Znane Pułapki
- **Brak `#Shorts` w tytule i hashtagach**: YouTube od 2024 roku automatycznie kwalifikuje wideo pionowe poniżej 60s jako Short. Dodanie `#Shorts` marnuje cenne znaki i obniża CTR.
- **Zakaz linków URL w opisach i komentarzach**: YouTube zablokował klikalność URL w Shortach (31.08.2023). Zamiast linków kieruj widza przez `related_video_id` (Powiązany film) oraz call-to-action w `pinned_comment`.
- **Długość tytułu**: `optimized_title` musi mieć **maksymalnie 45 znaków** (front-loaded), aby nie został ucięty wielokropkiem na urządzeniach mobilnych.
- **Przypięty komentarz**: Dodawany przez YouTube Comments API (`commentThreads.insert` / `commentsInsert`), wymusza otwarcie komentarzy i podbija retencję wideo (APV > 100%).

---

## Interfejs Standardowy Workera (Standard Agent Interface)

Zgodnie ze standardami architektury `media-dispatch`, `shorts-agent` implementuje metody bazowe:

```python
class ShortsAgent:
    def health_check(self) -> bool:
        """
        Sprawdza dostępność:
        1. Połączenia z YouTube Data API (ważność tokenu OAuth / API Key)
        2. Dostępności endpointu Short Machine (VSE API /v1/shorts/describe)
        3. Dostępności lokalnego katalogu roboczego C:\VSE\Shorts
        """
        pass

    def process(self, task: dict) -> dict:
        """
        Wykonuje zadanie z kolejki zadań:
        - scan_and_enrich: audyt i uzupełnienie opisów na YT przez POST /v1/shorts/describe
        - generate_schedule: wyliczenie kalendarza publikacji
        - dispatch_tiktok: przygotowanie paczki uploadu na TikTok
        """
        pass

    def get_status(self) -> dict:
        """
        Zwraca bieżący stan agenta, liczbę przetworzonych shortów,
        oczekujące zadania w harmonogramie i timestamp ostatniej operacji.
        """
        pass
```

---

## CLI Interface (Linia Poleceń)

Agent może być uruchamiany autonomicznie przez cron lub ręcznie z poziomu terminala:

```bash
# 1. Przeskanuj kanał i zaktualizuj brakujące opisy SEO (Short Machine)
python shorts_agent.py --scan

# 2. Przeskanuj z podglądem zmian bez faktycznej edycji na YouTube (Dry Run)
python shorts_agent.py --scan --dry-run

# 3. Zaktualizuj opis dla konkretnego shorta
python shorts_agent.py --update-description --video-id abc123shortId

# 4. Wygeneruj harmonogram publikacji dla katalogu filmu
python shorts_agent.py --schedule --input-dir "C:\VSE\Shorts\Debata_2026-09-01" --days 3

# 5. Wyświetl aktualny harmonogram i status publikacji
python shorts_agent.py --list-schedule

# 6. Uruchom trigger publikacji gotowych klipów na TikTok (Faza 5b)
python shorts_agent.py --upload-tiktok --schedule-file "shared/schedules/shorts_schedule.json"

# 7. Diagnostyka i health check
python shorts_agent.py --health
```

---

## Parametry CLI

| Parametr | Typ / Wartość | Opis |
|---|---|---|
| `--scan` | Flaga | Skanuje kanał YT i wysyła brakujące opisy do Short Machine (`/v1/shorts/describe`) |
| `--dry-run` | Flaga | Symulacja — nie wykonuje zapytań modyfikujących na YouTube/TikTok |
| `--video-id ID` | String | Identyfikator konkretnego filmu/shorta do przetworzenia |
| `--schedule` | Flaga | Uruchamia algorytm generowania harmonogramu |
| `--input-dir PATH` | Ścieżka | Katalog źródłowy z klipami (np. `C:\VSE\Shorts\...`) |
| `--days N` | Liczba (domyślnie: 3) | Na ile dni rozłożyć publikację puli shortów |
| `--list-schedule` | Flaga | Wyświetla podsumowanie zaplanowanych publikacji |
| `--upload-tiktok` | Flaga | Inicjuje proces uploadu gotowych klipów na TikTok |
| `--health` | Flaga | Wykonuje test połączeń i tokenów |

---

## Dane Wejściowe i Wyjściowe

### Dane Wejściowe (Input):
1. **YouTube Channel ID**: `UCoH2G9By4OX3kcLsc8lHgDw` (Studio Prawy_PL).
2. **Katalog lokalny**: `C:\VSE\Shorts\[Film]_[date]\` zawierający:
   - `*_raw.mp4` (surowe klipy wygenerowane przez VSE)
   - `*_gotowy.mp4` (zaakceptowane/zmontowane klipy)
   - `metadata.json` (kandydaci z VSE z hookami i timecode'ami)
3. **Tokeny Autoryzacyjne**:
   - OAuth2 token dla YouTube Data API (dostępny w bazie VSE przez `_build_credentials`)
   - JWT token do VSE API (`/v1/shorts/describe`)

### Dane Wyjściowe (Output):
1. **Zaktualizowane metadane wideo na YouTube**: Tytuł (max 45 zn, bez `#Shorts`), zoptymalizowany opis (150–350 zn, bez URL), tagi tematyczne, przypięty komentarz CTA.
2. **Harmonogram publikacji**: `shared/schedules/shorts_schedule.json`.
3. **Plik stanu i checkpoint**: `shared/state/shorts_agent_state.json`.

---

## Integracje Zewnętrzne

```
┌─────────────────────────────────────────────────────────────┐
│                        shorts-agent                         │
└──────┬───────────────────────┬───────────────────────┬──────┘
       │                       │                       │
       ▼                       ▼                       ▼
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│ YouTube Data │       │    Short     │       │    TikTok    │
│    API v3    │       │   Machine    │       │ Content API  │
│              │       │(/v1/shorts/  │       │  (Faza 5b)   │
│              │       │  describe)   │       │              │
└──────────────┘       └──────────────┘       └──────────────┘
```

1. **YouTube Data API v3**:
   - `search.list` / `playlistItems.list` — pobranie listy opublikowanych shortów.
   - `videos.list` — odczyt snippetu (tytuł, opis, tagi).
   - `videos.update` — zapis zoptymalizowanego opisu SEO i tytułu.
   - `commentThreads.insert` — dodanie i przypięcie komentarza CTA (APV loop).
2. **Short Machine (VSE Endpoint)**:
   - `POST /v1/shorts/describe` — generowanie zoptymalizowanego tytułu, opisu, hashtagów i przypiętego komentarza.
3. **TikTok API (Faza 5b)**:
   - Upload plików `*_gotowy.mp4` i przypisanie wygenerowanego opisu.

---

## Struktura Katalogów i Konwencja Nazewnictwa

```text
C:\VSE\Shorts\
  └── [Nazwa_Filmu]_[YYYY-MM-DD]\
        ├── [klip_1]_raw.mp4       # Wynik automatycznego renderingu VSE
        ├── [klip_1]_gotowy.mp4    # Wynik pracy człowieka - GATE DO PUBLIKACJI
        └── metadata.json          # Transkrypty i punkty podziału
```

> ⚠️ **Zasada Jakościowa**: Agent nigdy nie planuje publikacji na TikToku dla plików `*_raw.mp4`. Warunkiem koniecznym jest obecność pliku `*_gotowy.mp4`.

---

## Harmonogram Publikacji — Domyślne Sloty Godzinowe

Domyślna konfiguracja okien czasowych (możliwa do nadpisania w `config.json`):

- **Slot 1 (Poranek)**: `07:00 CEST`
- **Slot 2 (Południe)**: `12:00 CEST`
- **Slot 3 (Popołudnie)**: `18:00 CEST`
- **Slot 4 (Wieczór)**: `21:00 CEST`

---

## TODO i Otwarte Kwestie

- [ ] Implementacja klienta OAuth2 YouTube z automatycznym odświeżaniem tokena z bazy VSE.
- [ ] Implementacja mechanizmu detekcji braku opisu SM (`description.length < 50` / `mp4` filename title).
- [ ] Automatyczne dodawanie przypiętego komentarza na YouTube z pytaniem polaryzującym (`commentThreads.insert`).
- [ ] Decyzja dotycząca metody uploadu na TikTok (Direct API vs manual notification).

---

*[media-analyst | media-dispatch 31.08.2026] — specyfikacja agenta gotowa*  
*[media-dev-12 | media-dispatch 31.08.2026] — aktualizacja specyfikacji: Short Machine API /v1/shorts/describe aktywne na produkcji, reguły SEO 2026*
