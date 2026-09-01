# Raport z wdrożenia GmailSource przez PressAI API
**Callsign:** `media-dev-30`  
**Data:** 01.09.2026  
**Workspace:** `media-dispatch`  

---

## 1. Analiza PressAI Gmail API (`crimson-void`)

W repozytorium `crimson-void` w `backend/routers/gmail.py` zbadano pełną specyfikację endpointów Gmail pod prefixem `/api/gmail`:

| Endpoint | Metoda | Opis |
|---|---|---|
| `/api/gmail/accounts` | `GET` | Zwraca listę podłączonych kont Gmail dla danego użytkownika (`id`, `email`, `label`, `provider`, `last_synced`) |
| `/api/gmail/messages` | `GET` | Listuje wiadomości ze skrzynki. Parametry: `account_id` (int), `q` (string, standardowy query Gmail np. `in:inbox newer_than:1d`), `max_results` (int, max 50). Zwraca: `messages: [{id, subject, from, date, snippet, labels, has_attachments}]` |
| `/api/gmail/messages/{id}` | `GET` | Pobiera pełną treść konkretnego maila (`subject`, `from`, `to`, `date`, `text_body`, `html_body`, `attachments`, `labels`) |
| `/api/gmail/prepare-article` | `POST` | Ekstrahuje treść, załączniki (PDF, DOCX, obrazy) oraz linki z maila pod artykuł prasowy |
| `/api/gmail/auth/url` | `GET` | Generuje URL do autoryzacji OAuth Google |
| `/api/gmail/auth/callback` | `GET` | Callback OAuth dla Google |
| `/api/gmail/accounts/{id}` | `DELETE` | Odłącza konto Gmail |

### Wnioski z analizy API:
1. **Listowanie wiadomości:** PressAI **posiada** dedykowany endpoint `GET /api/gmail/messages` z pełną obsługą zapytań Gmail (`q`), stronicowaniem (`max_results`) oraz nagłówkami (`Subject`, `From`, `Date`, `Snippet`).
2. **Filtrowanie:** Działa zarówno po stronie Gmail API przez parametr `q` (np. `in:inbox newer_than:2d`), jak i lokalnie po `From` na białej liście nadawców.
3. **Autoryzacja:** Wymaga nagłówka `Authorization: Bearer <PRESSAI_JWT>`.

---

## 2. Implementacja `GmailSource`

Plik: `agents/base/sources/gmail_source.py`

### Kluczowe funkcjonalności:
- **Biała lista i priorytetyzacja nadawców (`PRIORITY_SENDERS`):**
  * `wei.org.pl` → WEI (P0, priority=9, portal=kurier365)
  * `bialykruk.pl` → Biały Kruk (P0, priority=8, portal=kurier365)
  * `rudinski` / `rudzinski` → Cezary Rudiński (P0, priority=9, portal=kurier365)
  * `binczyk` / `arkadiusz.binczyk` → Arkadiusz Bińczyk (P0, priority=8, portal=kurier365)
- **Auto-detekcja konta:** `_resolve_account_id()` automatycznie odpytuje `GET /api/gmail/accounts` i dopasowuje `account_id` dla konta `tobroz@gmail.com`.
- **Deduplikacja:** Plik stanu JSON (`/tmp/gmail_state_kurier365.json`) z buforem do 5000 identyfikatorów.
- **Ekstrakcja kandydatów:** `_message_to_candidate()` tworzy obiekty `ContentCandidate` z linkiem do Gmaila (`https://mail.google.com/mail/u/0/#inbox/{msg_id}`), sekcją `"Współpracownicy"`, statusem `pressai_prepared: False` oraz metadanymi.
- **Głębokie przetwarzanie (opcjonalne):** Metoda `prepare_article(message_id)` pozwala w razie potrzeby wywołać `POST /api/gmail/prepare-article`.
- **Obsługa błędów:** Graceful degradation przy braku tokenu lub błędzie `401 Unauthorized / gmail_reauth_required`.

---

## 3. Aktualizacja `Kurier365Worker`

Plik: `agents/kurier365-worker/worker.py`
- Zaktualizowano rejestrację `GmailSource` w `Kurier365Worker.__init__`:
  ```python
  self.add_source(GmailSource(
      pressai_url=pressai_url,
      portal='kurier365',
      token=pressai_token,
      hours_back=24,
      state_file='/tmp/gmail_state_kurier365.json'
  ))
  ```
- Poprawiono literówkę `handlers==[` na `handlers=[` w konfiguracji loggera.

---

## 4. Commity GitHub MCP

1. `agents/base/sources/gmail_source.py` — Commit SHA: `6d034212cfd557ebf9eb5a5b367e0507be9d4855`
2. `agents/base/sources/__init__.py` — Commit SHA: `75cde9ea1ca404bf9d9549e885c4d1171fe88bce`
3. `agents/kurier365-worker/worker.py` — Commit SHA: `a52096176f3ddcbe0927be5102b48df4af7b0188`

---
*Raport sporządził: media-dev-30 | media-dispatch 01.09.2026*
