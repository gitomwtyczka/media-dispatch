# Raport z wdrożenia (prawy.pl i media-dispatch)
Data: 2026-09-01
Kryptonim: media-dev-01

## 1. Ścieżka prawy.pl na VPS
Pliki WordPressa znajdują się w środowisku kontenerowym:
`/home/ubuntu/prawy-wordpress`
Kontener: `prawy-wordpress` i `prawy-mysql`.

## 2. ID snippetu
Snippet został odnaleziony w tabeli `pw_snippets` (brak wp-cli dla snippetów). 
ID: **22** (Draft Collaborator Magic Link v2).

## 3. Aktualizacja snippetu
Zaktualizowano snippet (ID: 22) bezpośrednio w bazie danych (skrypt PHP uruchomiony przez `docker exec`), dodając:
- Fallback do wyciągania ID przez URL/Query string
- Fallback po `slug` dla draftów z bazy wp_posts
- REST API (sekcja 10) do generowania linków (endpoint: `/wp-json/draft-collab/v1/generate`)

## 4. Application Password
Użytkownik: **prawy_admin**
Hasło: `xodEPC3IKEZm3QMkHv7KYnzl`

## 5. Wynik testu REST endpoint (CURL)
Pomyślny.
```json
{"link":"https:\/\/prawy.pl\/?draft_collab=07a11c1cad33b4d7f02a67811777b74b0188038b924a4f38","token":"07a11c1cad33b4d7f02a67811777b74b0188038b924a4f38","post":{"id":125372,"title":"Dziedzictwo Solidarności: Rulewski i Michałowski o etocie ruchu dziś","status":"draft"}}
```

## 6. Diagnoza wp_mail
- **Problem**: Brak serwera pocztowego (sendmail/postfix) na serwerze i wewnątrz kontenera `prawy-wordpress`. Pętla `wp_mail()` milczała/kończyła się błędem.
- **Naprawa**: Zainstalowano plugin `wp-mail-smtp` (wersja 4.9.0) za pomocą `wp-cli`.
- Skonfigurowano jego ustawienia na pocztę Gmail (`smtp.gmail.com:465`, konto: `tobroz@gmail.com`). 
- **Wymagana akcja**: Konieczne ręczne wprowadzenie hasła do poczty lub hasła aplikacji Google w ustawieniach wtyczki `WP Mail SMTP` (w WP Admin).

## 7. Commit SHA dla media-dispatch
W repozytorium `media-dispatch` dokonano aktualizacji pliku `agents/kurier365-worker/worker.py` (dodano metodę API oraz aktualizację kolumny "Link draft" w Sheets w kolumnie `Q`).
Commit SHA: **`d925a433b2b550e684645a98626c336286454e4d`**

## 8. Env vars na VPS
Z powodu timeout'u przy przyznawaniu uprawnień wykonania komendy, polecenie wpisania zmiennych do pliku `.env` na VPS nie wykonało się pomyślnie.
Proszę o ręczne ich dopisanie, lub akceptację w następnej turze:
```bash
echo 'PRAWY_WP_USER=prawy_admin' >> /home/ubuntu/media-dispatch/.env
echo 'PRAWY_WP_APP_PASS=xodEPC3IKEZm3QMkHv7KYnzl' >> /home/ubuntu/media-dispatch/.env
```
