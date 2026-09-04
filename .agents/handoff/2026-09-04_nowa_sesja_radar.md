# Handoff: media-strateg -> Nowa Sesja [04.09.2026]

## Cel nowej sesji
Przeprowadzenie testów nowej logiki Workera w zakresie `content radar` oraz systemu scrapującego po witrynach. Równolegle: gruntowna naprawa modułu `gmail_source.py` zgodnie z precyzyjnymi wytycznymi Redaktora.

## Punkt startowy (GitHub MCP jest zsynchronizowany)
Wszystkie zmiany z poprzednich sesji (Kaganiec JWT `Fail-Fast`, parametry CLI `--source`) zostały **zsynchronizowane z repozytorium GitHub** (branch `main`). Możesz i powinieneś bezpiecznie bazować na GitHub MCP jako jedynym źródle prawdy.

## KLUCZOWE WYTYCZNE (Błędy do naprawienia od zaraz)

### 1. GmailSource: Filtrowanie po twardych adresach E-mail
Poprzedni skład błędnie wdrożył wyszukiwanie priorytetów używając podciągów w locie (display names). 
**Polecenie Redaktora:** Imiona i nazwiska były potrzebne *wyłącznie operacyjnie* do zdiagnozowania właściwych adresów nadawców. Skrypt ma filtrować inbox twardo po wyciągniętych adresach e-mail, a nie po imionach z nagłówków. Należy naprawić tę logikę.

### 2. GmailSource: Rozróżnianie "Wymiany zdań" od "Materiału"
System błędnie wyciągał krótkie "pingi", a ignorował maile z paczkami załączników (Bińczyk, Rudziński).
**Polecenie Redaktora:** Należy zaimplementować mechanizm, który odróżni maile będące krótką wymianą zdań od pełnoprawnych materiałów redakcyjnych. 
Heurystyka powinna uwzględniać:
- Obecność i typ załączników (PDF, JPG).
- Objętość/długość treści wiadomości.
- Kluczowe frazy (np. "zaproszenie", "materiały prasowe").

### 3. Osobiste testy Content Radar
Agent ma za zadanie przeprowadzić testy `content radar` oraz systemu sprawdzającego po witrynach pod bezpośrednim nadzorem Redaktora.
Skrypt workera: `agents/kurier365-worker/worker.py` (posiada już wbudowaną flagę izolującą np. `--source`). Pamiętaj o absolutnym zakazie publikacji bez zatwierdzenia.