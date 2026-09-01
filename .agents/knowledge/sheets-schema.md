# Dokumentacja Google Sheets — "Nagrania prawy"

Ten dokument opisuje strukturę i przeznaczenie głównego pliku Google Sheets używanego w przepływie pracy produkcji wideo i publikacji artykułów na prawy.pl.

**ID Arkusza (Spreadsheet ID):** `1zqwvS784EaZh1EJIcXk1DliAau1r4X15ENFJjloDSaM`
**Uwierzytelnianie automatyczne na serwerze (VPS):** `/home/ubuntu/otwock-data/muzeum/muzeum-drive-sa.json`

## Złota zasada
Nie twórz nowych arkuszy do śledzenia statusu filmów i artykułów. Użytkownik wykorzystuje arkusze `Emisja`, `Kandydaci YT`, `Biblia` i `Shorty` do zarządzania stanem. Jeśli szukasz powiązania np. wideo YouTube -> URL szkicu WordPress, znajduje się to już w odpowiednim arkuszu w odpowiedniej kolumnie jako hiperlink (nie surowy tekst, patrz "Uwaga technologiczna" poniżej).

## Uwaga technologiczna dla skryptów (Google Sheets API)
Kolumny zawierające linki mogą wyglądać jako zwykły tekst pod przyciskiem/ikony.
Gdy odpytujesz Sheets API, **ZBLOKOWANE SĄ** one pod `includeGridData=True`. URL znajduje się w obiekcie komórki:
```python
# Przykład wydobycia linku z komórki
cell = row_data[kolumna].get('hyperlink')
if not cell:
    formula = cell.get('userEnteredValue', {}).get('formulaValue', '')
    if formula.upper().startswith('=HYPERLINK'):
        cell = formula.split('"')[1]
```

## Arkusze (Zakładki)

### 1. `Emisja` (GID: 809929940)
Główny arkusz planowania publikacji i powiązań między VSE, YouTube a WordPress.
**Struktura kolumn:**
- `Lp`, `YouTube ID`, `Tytuł`, `Krótki opis`, `Czas trwania`
- `YT URL`
- `WP Draft URL` (Kluczowa kolumna! Zawiera HIPERLINKI do draftów WP)
- `Data emisji`, `Godzina emisji`
- `Status`, `Notatki`
- `Shorty`, `Short Machine`
- `Tytuł SEO`, `Frazy kluczowe`
- `Gość / Rozmówca`, `Prowadzący`, `Kategoria WP`
- `Link draft` (Kolumna wprowadzona 01.09.2026, zawiera linki collab)

### 2. `Biblia`
Planowanie serii biblijnej.
**Struktura kolumn:**
- `Data`, ``, `Rodział`, ``, ``, ``
- `emisja` (data)
- `prawy.pl` (HIPERLINKI lub surowe URL do opublikowanych wpisów na prawy.pl)
- `spotify`, `youtube`, `mp3`, `sezon`, `numer`

### 3. `Kandydaci YT`
Zbieranie potencjalnych filmów do obróbki (wynik działania radarów / detekcji).
**Struktura kolumn:**
- `YT ID`, `Data wykrycia`, `Tytuł YT`, `Czas trwania`, `Napisy`, `Trend Score`, `Status`, `Uwagi`, `WP Post ID`, `Data emisji`

### 4. `Shorty`
Statusy przyciętych shortów wygenerowanych z VSE.

---
*Aktualizacja: 01.09.2026 (media-strateg)*