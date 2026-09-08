# Dokumentacja Google Sheets — "Nagrania prawy"

Ten dokument opisuje pełną strukturę i przeznaczenie głównego skoroszytu Google Sheets używanego w przepływie pracy produkcji wideo (VSE), artykułów tekstowych (PressAI) i publikacji na portale `prawy.pl`, `kurier365.pl` oraz `biznesciti.com`.

**ID Arkusza (Spreadsheet ID):** `1zqwvS784EaZh1EJIcXk1DliAau1r4X15ENFJjloDSaM`  
**Główny Service Account (media-dispatch):** `media-dispatch-sheets@antigravity-mcp-keys.iam.gserviceaccount.com`  
**Ścieżka SA na VPS:** `/home/ubuntu/media-dispatch/config/service_account.json` (zmienna środowiskowa `GOOGLE_SA_FILE`)  
**Poprzedni Service Account (fallback):** `/home/ubuntu/otwock-data/muzeum/muzeum-drive-sa.json`

---

## Złota zasada
Nie twórz nowych zewnętrznych arkuszy ani plików do śledzenia statusu filmów i artykułów. Użytkownik oraz boty redakcyjne wykorzystują dedykowane zakładki tego jednego skoroszytu do zarządzania stanem. Jeśli szukasz powiązania wideo YouTube -> URL szkicu WordPress lub propozycji artykułów -> wygenerowany draft WP, znajduje się to już w odpowiedniej zakładce w odpowiedniej kolumnie jako hiperlink lub status.

---

## Uwaga technologiczna dla skryptów (Google Sheets API)
Kolumny zawierające linki mogą w arkuszu wyglądać jak zwykły tekst pod przyciskiem lub etykietą.
Gdy odpytujesz Sheets API, **ZBLOKOWANE SĄ** one pod `includeGridData=True`. URL znajduje się w obiekcie komórki:
```python
# Przykład wydobycia linku z komórki
cell = row_data[kolumna].get('hyperlink')
if not cell:
    formula = cell.get('userEnteredValue', {}).get('formulaValue', '')
    if formula.upper().startswith('=HYPERLINK'):
        cell = formula.split('"')[1]
```

---

## Zakładki Propozycji (Nowy Standard — 08.09.2026)

Trzy dedykowane zakładki przeznaczone do gromadzenia propozycji artykułów generowanych z wywiadu (Feed Crawler, Content Radar, Gmail) dla poszczególnych portali.

### Wspólna struktura kolumn (A–H)
Wszystkie zakładki typu *Propozycje* posiadają identyczny układ 8 kolumn:
- **A — Temat**: Oryginalny tytuł lub skrócony opis tematu ze źródła.
- **B — Źródło**: Nazwa agencji, medium lub domeny (np. PAP, Reuters, wPolityce).
- **C — Link do źródła**: Bezpośredni URL do artykułu źródłowego (kluczowy dla modułu Extract w PressAI).
- **D — Data**: Data i godzina publikacji materiału źródłowego (`Data opublikowania źródła`).
- **E — Tytuł SEO**: Proponowany chwytliwy tytuł artykułu zoptymalizowany pod wyszukiwarki.
- **F — Frazy kluczowe**: Słowa kluczowe (oddzielone przecinkami) wspierające pozycjonowanie.
- **G — Obrazek główny**: URL lub ścieżka do sugerowanej grafiki / zdjęcia.
- **H — Status**: Pole sterujące akcjami redaktora i skryptów sync.

### Dopuszczalne wartości Status (Dropdown):
- `Nowa Propozycja` — domyślna wartość nadawana przy automatycznym zasilaniu przez bota.
- `Publikuj w PressAI` — polecenie dla bota sync: pobierz artykuł źródłowy, wygeneruj treść w PressAI i utwórz szkic (`draft`) w WordPress.
- `Publikuj VSE` — *(w planach)* polecenie przekazania materiału wideo do pipeline VSE.
- `Odrzucone` — propozycja odrzucona przez redaktora; pomijana przez skrypty publikujące.
- `Opublikowane` — status ustawiany automatycznie przez skrypt synchronizujący po pomyślnym utworzeniu wpisu w WordPress.

---

### 1. `Propozycje Radar` (GID: 514074648)
- **Portal docelowy:** `prawy.pl`
- **Profil tematyczny:** Polityka, Kościół, tożsamość narodowa, patriotyzm, społeczeństwo, sprawy bieżące.
- **Worker zasilający:** Feed Crawler / Content Radar (`radar-worker`).
- **Worker synchronizujący:** `agents/radar-worker/radar_sheets_sync.py` (uruchamiany w cronie co godzinę o `:30`).
- **Status dropdown:** `[Nowa Propozycja | Publikuj w PressAI | Odrzucone | Opublikowane]`.

### 2. `Propozycje Kurier365` (GID: 1073549292)
- **Portal docelowy:** `kurier365.pl`
- **Profil tematyczny:** Wiadomości ogólne, geopolityka, sprawy międzynarodowe, technologia, nauka, edukacja, społeczeństwo.
- **Worker zasilający:** `agents/kurier365-worker/worker.py` (uruchamiany w cronie co 6 godzin: `0 */6 * * *`).
- **Worker synchronizujący:** `agents/kurier365-worker/kurier365_sheets_sync.py` (uruchamiany w cronie co godzinę o `:15`).
- **Status dropdown:** `[Nowa Propozycja | Publikuj w PressAI | Odrzucone | Opublikowane]`.

### 3. `Propozycje BiznesCiti` (GID: 1900951726)
- **Portal docelowy:** `biznesciti.com`
- **Profil tematyczny:** Biznes, rynki finansowe, inwestycje, gospodarka, nieruchomości, prawo gospodarcze, spółki.
- **Worker zasilający:** `agents/kurier365-worker/worker.py` (po poprawce routingu dla kategorii biznesowych).
- **Worker synchronizujący:** `agents/biznesciti-worker/biznesciti_sheets_sync.py` (uruchamiany w cronie co godzinę o `:45`).
- **Status dropdown:** `[Nowa Propozycja | Publikuj w PressAI | Odrzucone | Opublikowane]`.

---

## Pozostałe Zakładki Skoroszytu

### 4. `Emisja` (GID: 809929940)
Główny arkusz planowania publikacji i powiązań między VSE, YouTube a WordPress (`prawy.pl`).
- **Worker synchronizujący:** `agents/emisja-worker/emisja_sheets_sync.py` (uruchamiany w cronie co godzinę o `:00`).
- **Struktura kolumn:**
  - `Lp`, `YouTube ID`, `Tytuł`, `Krótki opis`, `Czas trwania`
  - `YT URL`
  - `WP Draft URL` (Kluczowa kolumna! Zawiera HIPERLINKI do draftów WP)
  - `Data emisji`, `Godzina emisji`
  - `Status`, `Notatki`
  - `Shorty`, `Short Machine`
  - `Tytuł SEO`, `Frazy kluczowe`
  - `Gość / Rozmówca`, `Prowadzący`, `Kategoria WP`
  - `Link draft` (zawiera linki collab)

### 5. `Biblia` (GID: 893663019)
Planowanie publikacji serii Prawy Biblijny.
- **Worker synchronizujący:** `agents/vse-worker/scripts/biblia_full_pipeline.py` (pipeline audio/tekst do VSE i WP).
- **Struktura kolumn:**
  - `Data`, ``, `Rozdział`, ``, ``, ``
  - `emisja` (data)
  - `prawy.pl` (HIPERLINKI lub surowe URL do opublikowanych wpisów na prawy.pl)
  - `spotify`, `youtube`, `mp3`, `sezon`, `numer`

### 6. `Shorty` (GID: 767494598)
Statusy przyciętych krótkich materiałów wideo (YouTube Shorts, Reels, TikTok) generowanych z silnika VSE / Shorts Machine.
- **Skrypty pomocnicze:** `agents/vse-worker/scripts/process_shorts_describe.py`.

### 7. `Kandydaci YT` (GID: 1644472360)
Zbieranie potencjalnych filmów do obróbki (wynik działania radarów i detekcji nowych nagrań).
- **Struktura kolumn:**
  - `YT ID`, `Data wykrycia`, `Tytuł YT`, `Czas trwania`, `Napisy`, `Trend Score`, `Status`, `Uwagi`, `WP Post ID`, `Data emisji`.

### 8. `Nagrania` (GID: 0)
Historyczna baza i ewidencja nagrań archiwalnych portalu Prawy.pl.

### 9. `Content Radar` (GID: 328988894)
Poprzednia, archiwalna wersja zakładki propozycji radaru dla Prawy.pl (zastępowana przez `Propozycje Radar`).

### 10. `Ostatnie niepubliczne` (GID: 1844067239)
Monitoring i ewidencja filmów przesłanych na kanał YouTube jako niepubliczne (`unlisted`) przed ich oficjalną premierą.

---
*Aktualizacja: 08.09.2026 (Supervisor 03) — dodano opisy nowych zakładek Propozycje*
