# FIX OVERNIGHT: Shorts z 30 sierpnia i Arkusz Google

## Kontekst (Błąd do naprawienia)
Poprzedni subagent próbował zaktualizować 5 starszych shortów na YT, ale użył błędnego skryptu mapującego (prawdopodobnie zmienna nadpisała mu się w pętli). W rezultacie wszystkie 5 shortów dostało ten sam Hook/Puentę z filmu o Wolińskiej ("Muzeum Polin organizuje dyskusję...").

## Zadanie dla Agenta /goal
1. **Odtworzyć właściwe opisy dla 5 shortów**:
   - mw6A9CZ6DuM (Monachium 1938)
   - mTyr64ygkJU (Sejm to leniwe ciało)
   - 8nbA6YSZAVQ (Gdyby PiS tak zrobiło)
   - slA15REfjpU (Dualizm władzy niszczy Polskę)
   - lX2vvs8E-AY (Jedwabne)
   Należy wyciągnąć je z `short_candidate_sets` (baza `vse-postgres` na VPS).

2. **Zaktualizować YouTube**:
   - Naprawić tytuły i opisy na YT dla tych 5 shortów.
   - Pobrać token OAuth YouTube'a ze skryptu `_build_credentials` (jak opisano w `vse-worker-constitution.md`).
   - UWAGA: API YouTube nie pozwala na ustawienie "Podobnego filmu" – ignorujemy to dla skryptu, użytkownik zrobi to rano.

3. **Zaktualizować Arkusz Google**:
   - Link: `https://docs.google.com/spreadsheets/d/1zqwvS784EaZh1EJIcXk1DliAau1r4X15ENFJjloDSaM/edit?gid=767494598#gid=767494598`
   - Arkusz nazywa się zapewne "Shorty". Należy ustawić w wierszach 6-10 status "zaplanowane" (lub podobny) oraz zaktualizować datę (5-9 września).
   - W kontenerze `vse-api` pod `/app` leży plik `muzeum-drive-sa.json` - to jest Service Account do Google Sheets (gspread). Użyj go!

## Techniczne wytyczne dla Agenta:
- Pisz ZBIORCZE skrypty w Pythonie lokalnie przez `write_to_file`, przerzucaj przez `scp` do VPS i wykonuj raz. Unikniesz w ten sposób zawieszania się.
- Zanim zaktualizujesz YT, zrób query do bazy SQL i dokładnie dopasuj ID wideo z bazy (lub teksty) do docelowych shortów!
