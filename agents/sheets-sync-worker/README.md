# Sheets Sync Worker

Moduł synchronizacji harmonogramu editorial z Google Sheets dla `media-dispatch`.

## Arkusz docelowy
- **URL**: [Google Sheets Harmonogram](https://docs.google.com/spreadsheets/d/1zqwvS784EaZh1EJIcXk1DliAau1r4X15ENFJjloDSaM/edit?gid=809929940)
- **Sheet ID**: `1zqwvS784EaZh1EJIcXk1DliAau1r4X15ENFJjloDSaM`
- **GID**: `809929940`

---

## Nowe kolumny
W tabeli dodano 4 nowe kolumny po kolumnie `Notatki` (kolumny L, M, N, O):
1. **Shorty** (ile gotowych/wyrenderowanych)
2. **Short Machine** (TAK / NIE / W TOKU)
3. **Tytuł SEO** (zatwierdzony tytuł SEO max 60 zn)
4. **Frazy kluczowe** (2-3 główne frazy SEO)

---

## Uruchomienie skryptu

### Wymagania wstępne:
```bash
pip install gspread google-auth
```

### Opcja 1: Uruchomienie z kluczem konta usługi (Service Account)
1. Pobierz plik JSON konta usługi z Google Cloud Console.
2. Nadaj uprawnienia edycji kontu usługi (jego adres email) do arkusza Google Sheets.
3. Uruchom:
```bash
python update_editorial.py --service-account path/to/service_account.json
```

### Opcja 2: Uruchomienie z OAuth (przeglądarkowe logowanie użytkownika)
```bash
python update_editorial.py --oauth
```

### Opcja 3: Eksport do CSV / TSV lub podgląd Dry-Run
```bash
# Podgląd w konsoli
python update_editorial.py --dry-run

# Eksport do pliku CSV
python update_editorial.py --export-csv harmonogram_update.csv

# Eksport do pliku TSV (idealny do bezpośredniego wklejenia Tab-separated w Sheets)
python update_editorial.py --export-tsv harmonogram_update.tsv
```

---

## Plik z danymi gotowy do importu
W tym katalogu znajduje się również gotowy plik:
- [`editorial_schedule_Lp10-14.csv`](editorial_schedule_Lp10-14.csv)
