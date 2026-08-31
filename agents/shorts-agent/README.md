# shorts-agent

Dedykowany agent zarządzający formatem krótkim (Shorts / Reels / TikTok) dla kanału **Studio Prawy_PL** w architekturze `media-dispatch`.
Odpowiada za audyt opublikowanych shortów, generowanie brakujących opisów SEO przez **Short Machine**, aktualizację YouTube Data API oraz harmonogramowanie dystrybucji.

---

## Co robi

1. **Skanuje kanał YouTube Studio Prawy_PL** (`UCoH2G9By4OX3kcLsc8lHgDw`) pod kątem opublikowanych filmów typu Short.
2. **Weryfikuje jakość SEO opisu każdego shorta**:
   - Wykrywa shorty z pustym opisem lub brakiem zoptymalizowanych znaczników/hashtagów.
   - Przekazuje identyfikator/URL shorta do **Short Machine** (moduł VSE).
   - Aktualizuje opis, tagi i przypięty komentarz na YouTube przez YouTube Data API v3.
3. **Planuje harmonogram publikacji (Scheduling Engine)**:
   - Grupuje surowe/gotowe klipy (~6 z jednego filmu głównego z `C:\VSE\Shorts\[Film]_[date]\`).
   - Rozkłada publikacje w czasie na 2–6 dni.
   - Dopasowuje publikacje do okien szczytowej oglądalności (`07:00`, `12:00`, `18:00`, `21:00`).
   - Generuje wyjściowy plik `shared/schedules/shorts_schedule.json`.
4. **Wspiera dystrybucję TikTok (Faza 5b)**:
   - Integruje się z `tiktok-worker` i przekazuje gotowe pliki `*_gotowy.mp4` wraz z opisami SEO do publikacji na profilu TikTok.

---

## Interfejs Standardowy Workera (Standard Agent Interface)

Zgodnie ze standardami architektury `media-dispatch`, `shorts-agent` implementuje metody bazowe:

```python
class ShortsAgent:
    def health_check(self) -> bool:
        """
        Sprawdza dostępność:
        1. Połączenia z YouTube Data API (ważność tokenu OAuth / API Key)
        2. Dostępności endpointu Short Machine (VSE API /v1/shorts/seo-description)
        3. Dostępności lokalnego katalogu roboczego C:\VSE\Shorts
        """
        pass

    def process(self, task: dict) -> dict:
        """
        Wykonuje zadanie z kolejki zadań:
        - scan_and_enrich: audyt i uzupełnienie opisów na YT
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
| `--scan` | Flaga | Skanuje kanał YT i wysyła brakujące opisy do Short Machine |
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
   - JWT token do VSE API (`/v1/shorts/seo-description`)

### Dane Wyjściowe (Output):
1. **Zaktualizowane metadane wideo na YouTube**: Tytuł z `#Shorts`, zoptymalizowany opis, tagi tematyczne, przypięty komentarz CTA.
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
│              │       │  (VSE Engine)│       │  (Faza 5b)   │
└──────────────┘       └──────────────┘       └──────────────┘
```

1. **YouTube Data API v3**:
   - `search.list` / `playlistItems.list` — pobranie listy opublikowanych shortów.
   - `videos.list` — odczyt snippetu (tytuł, opis, tagi).
   - `videos.update` — zapis zoptymalizowanego opisu SEO.
   - `commentThreads.insert` — dodanie i przypięcie komentarza z linkiem do pełnego filmu.
2. **Short Machine (VSE Endpoint / Moduł)**:
   - `POST /v1/shorts/seo-description` — generowanie chwytliwego hooku, opisu i hashtagów.
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
- [ ] Opracowanie promptu Short Machine pod kątem specyfiki algorytmu YouTube Shorts vs TikTok.
- [ ] Decyzja dotycząca metody uploadu na TikTok (Direct API vs manual notification).
- [ ] Automatyczne dodawanie przypiętego komentarza na YouTube z linkiem do odcinka głównego.

---

*[media-analyst | media-dispatch 31.08.2026] — specyfikacja agenta gotowa*
