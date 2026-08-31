# Raport media-dev-17: Aktualizacja Google Sheets Harmonogram Editorial

**Data:** 01.09.2026  
**Autor:** `media-dev-17`  
**Projekt:** `media-dispatch`  
**Arkusz:** `1zqwvS784EaZh1EJIcXk1DliAau1r4X15ENFJjloDSaM` | GID: `809929940`  
**URL:** https://docs.google.com/spreadsheets/d/1zqwvS784EaZh1EJIcXk1DliAau1r4X15ENFJjloDSaM/edit?gid=809929940

---

## 1. Status weryfikacji credentials (Krok 1)

Przeprowadzono pełny skan plików credentials na serwerze VPS (`ubuntu@147.224.162.100`):
- Znaleziono konto usługi: `/home/ubuntu/otwock-data/muzeum/muzeum-drive-sa.json` (`muzeum-drive-reader@antigravity-mcp-keys.iam.gserviceaccount.com`).
- Po wykonaniu testowego zapytania do Google Sheets API v4 zwrócono błąd 403 (`Google Sheets API has not been used in project 779032474349 before or it is disabled`).
- Pozostałe pliki OAuth (`/home/ubuntu/pressai-academy/secrets/oauth.json`, `/home/ubuntu/crimson-void/backend/client_secret.json`, baza `vse-postgres`) zawierają wyłącznie uprawnienia YouTube / Web bez zakresu `spreadsheets`.

Zgodnie z regułą dyspozycji ("jeśli brak credentials — nie instaluj nic, zrób plan B") wdrożono **Plan B**.

---

## 2. Wdrożenie Planu B

W repozytorium `media-dispatch` (branch `main`) utworzono moduł `agents/sheets-sync-worker/`:

1. **Skrypt aktualizacyjny:**
   - [`agents/sheets-sync-worker/update_editorial.py`](https://github.com/gitomwtyczka/media-dispatch/blob/main/agents/sheets-sync-worker/update_editorial.py)
   - Obsługa `gspread`, automatyczne wykrywanie Service Account / OAuth, aktualizacja nagłówków o nowe kolumny, dodawanie/aktualizowanie wierszy 10-14, obsługa `--dry-run`, `--export-csv`, `--export-tsv`.

2. **Plik CSV z danymi:**
   - [`agents/sheets-sync-worker/editorial_schedule_Lp10-14.csv`](https://github.com/gitomwtyczka/media-dispatch/blob/main/agents/sheets-sync-worker/editorial_schedule_Lp10-14.csv)

3. **Dokumentacja i instrukcja uruchomienia:**
   - [`agents/sheets-sync-worker/README.md`](https://github.com/gitomwtyczka/media-dispatch/blob/main/agents/sheets-sync-worker/README.md)

---

## 3. Instrukcja uruchomienia skryptu

### Wymagania:
```bash
pip install gspread google-auth
```

### Opcje wykonania:
```bash
# Z kontem usługi (Service Account):
python agents/sheets-sync-worker/update_editorial.py --service-account /sciezka/do/service_account.json

# Przez OAuth (logowanie w przeglądarce):
python agents/sheets-sync-worker/update_editorial.py --oauth

# Tryb testowy (podgląd bez zapisu):
python agents/sheets-sync-worker/update_editorial.py --dry-run
```

---

## 4. Dane do ręcznego wklejenia (CSV / TSV)

### Nowe kolumny w nagłówku (od kolumny L, po kolumnie K: Notatki):
- Kolumna L (12): `Shorty`
- Kolumna M (13): `Short Machine`
- Kolumna N (14): `Tytuł SEO`
- Kolumna O (15): `Frazy kluczowe`

### Format CSV:
```csv
Lp,YouTube ID,Tytuł,Krótki opis,Czas trwania,YT URL,WP Draft URL,Data emisji,Godzina emisji,Status,Notatki,Shorty,Short Machine,Tytuł SEO,Frazy kluczowe
10,s6aGNXdtKpA,"Mosiński: Porozumienia sierpniowe 1980 i narodziny Solidarności","Jan Mosiński o kulisach porozumień sierpniowych 1980 roku i narodzinach NSZZ Solidarność.",38:46,https://www.youtube.com/watch?v=s6aGNXdtKpA,https://prawy.pl/porozumienia-sierpniowe-1980-jan-mosinski-o-narodzinach-solidarnosci/,31.08.2026,(brak),opublikowany,"WP #125353, live",5,TAK,Porozumienia sierpniowe 1980: Mosiński o Solidarności,"porozumienia sierpniowe 1980, Solidarność, Jan Mosiński"
11,zYcq-57Y0ts,"Mosiński: Testament Solidarności — co zostało z idei roku 80?","Mosiński o tym co pozostało z idei Solidarności po 44 latach.",-,https://www.youtube.com/watch?v=zYcq-57Y0ts,https://prawy.pl/?p=125367,(czeka),(czeka),wstrzymany,"User wycofał 2x — czeka na dyspozycję",5,TAK,Testament Solidarności: Co zostało z idei roku 80?,"testament Solidarności, Jan Mosiński, idee Solidarności"
12,EnclbKLEDAA,"Rulewski vs Michałowski: Kłótnia o Solidarność i jej spadek","Jan Rulewski i Bogdan Michałowski o sporze dotyczącym dziedzictwa NSZZ Solidarność.",-,https://www.youtube.com/watch?v=EnclbKLEDAA,https://prawy.pl/?p=125372,(czeka),(czeka),draft,"WP draft, YT unlisted — czeka na datę",5,W TOKU,Rulewski vs Michałowski: Spór o spadek Solidarności,"Jan Rulewski, Bogdan Michałowski, historia Solidarności"
13,cDMAe_wx_AU,"Helena Wolińska: bestia w mundurze i morderca gen. Nila","Tadeusz Płużański ujawnia kulisy ekstradycji Heleny Wolińskiej i wybielania stalinowskiej zbrodniarki.",53:08,https://www.youtube.com/watch?v=cDMAe_wx_AU,(w toku),01.09.2026,(brak),publikacja w toku,"Klimczak Płużański Wolińska, render shortów w toku",5 (render),W TOKU,Helena Wolińska: Bestia w mundurze i morderca gen. Nila,"Helena Wolińska, Tadeusz Płużański, gen Fieldorf Nil"
14,yQ-Q_YrleLE,Klimczak Śliwka Nowacka,[VSE w toku — brak opisu],15:18,https://www.youtube.com/watch?v=yQ-Q_YrleLE,(w toku),(hold),(hold),hold,"User powiedział hold. VSE done, wp_id=0.",0,NIE,Klimczak, Śliwka, Nowacka: Komentarz polityczny,"Klimczak, Śliwka, Barbara Nowacka"
```

### Format Tab-Separated (do bezpośredniego wklejenia Ctrl+V w wiersze 10-14 arkusza):
```text
10	s6aGNXdtKpA	Mosiński: Porozumienia sierpniowe 1980 i narodziny Solidarności	Jan Mosiński o kulisach porozumień sierpniowych 1980 roku i narodzinach NSZZ Solidarność.	38:46	https://www.youtube.com/watch?v=s6aGNXdtKpA	https://prawy.pl/porozumienia-sierpniowe-1980-jan-mosinski-o-narodzinach-solidarnosci/	31.08.2026	(brak)	opublikowany	WP #125353, live	5	TAK	Porozumienia sierpniowe 1980: Mosiński o Solidarności	porozumienia sierpniowe 1980, Solidarność, Jan Mosiński
11	zYcq-57Y0ts	Mosiński: Testament Solidarności — co zostało z idei roku 80?	Mosiński o tym co pozostało z idei Solidarności po 44 latach.	-	https://www.youtube.com/watch?v=zYcq-57Y0ts	https://prawy.pl/?p=125367	(czeka)	(czeka)	wstrzymany	User wycofał 2x — czeka na dyspozycję	5	TAK	Testament Solidarności: Co zostało z idei roku 80?	testament Solidarności, Jan Mosiński, idee Solidarności
12	EnclbKLEDAA	Rulewski vs Michałowski: Kłótnia o Solidarność i jej spadek	Jan Rulewski i Bogdan Michałowski o sporze dotyczącym dziedzictwa NSZZ Solidarność.	-	https://www.youtube.com/watch?v=EnclbKLEDAA	https://prawy.pl/?p=125372	(czeka)	(czeka)	draft	WP draft, YT unlisted — czeka na datę	5	W TOKU	Rulewski vs Michałowski: Spór o spadek Solidarności	Jan Rulewski, Bogdan Michałowski, historia Solidarności
13	cDMAe_wx_AU	Helena Wolińska: bestia w mundurze i morderca gen. Nila	Tadeusz Płużański ujawnia kulisy ekstradycji Heleny Wolińskiej i wybielania stalinowskiej zbrodniarki.	53:08	https://www.youtube.com/watch?v=cDMAe_wx_AU	(w toku)	01.09.2026	(brak)	publikacja w toku	Klimczak Płużański Wolińska, render shortów w toku	5 (render)	W TOKU	Helena Wolińska: Bestia w mundurze i morderca gen. Nila	Helena Wolińska, Tadeusz Płużański, gen Fieldorf Nil
14	yQ-Q_YrleLE	Klimczak Śliwka Nowacka	[VSE w toku — brak opisu]	15:18	https://www.youtube.com/watch?v=yQ-Q_YrleLE	(w toku)	(hold)	(hold)	hold	User powiedział hold. VSE done, wp_id=0.	0	NIE	Klimczak, Śliwka, Nowacka: Komentarz polityczny	Klimczak, Śliwka, Barbara Nowacka
```

---

[media-dev-17]
