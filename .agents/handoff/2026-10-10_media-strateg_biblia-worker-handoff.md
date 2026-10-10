# Handoff: media-strateg -> biblia-worker (2026-10-10)

## 1. Stan biblia-workera
- **Lokalizacja:** `agents/biblia-worker/`
- **Co potrafi:** Pełny proces publikacji i sprawdzania batchy (YT + WP). Posiada flagi: `--execute`, `--dry-run`, `--patch-meta`, `--ids-file`.
- **Testy:** Zaimplementowano 11+ testów.
- **SHA ostatnich commitów:** `485428e7c38abc05f33747c3ba25b7cb609ea586` (ostatni commit w repo)

## 2. Wynik batcha 11-17.10 (Kanał: Prawy Biblijny UCNXh5eIlMVxnUBpTMKUp4CA)

| Data | YT ID | WP ID | WP OK | YT OK | Usterki |
|------|-------|-------|-------|-------|---------|
| 11.10 | In5b5-k-O2Q | 127909 | NIE | TAK | WP podcast_show (jest: brak, ma być: prawy-biblijny), WP kategorie (jest: Biblia + Uncategorized, ma być: tylko Biblia) |
| 12.10 | SdLkNmBS3uk | 127914 | NIE | TAK | WP podcast_show (jest: brak, ma być: prawy-biblijny), WP kategorie (jest: Biblia + Uncategorized, ma być: tylko Biblia) |
| 13.10 | uP6y29-2QAU | 127918 | NIE | TAK | WP podcast_show (jest: brak, ma być: prawy-biblijny), WP kategorie (jest: Biblia + Uncategorized, ma być: tylko Biblia) |
| 14.10 | gctzm-CTd80 | 127925 | NIE | TAK | WP podcast_show (jest: brak, ma być: prawy-biblijny), WP kategorie (jest: brak, ma być: Biblia) |
| 15.10 | M1bVv8k6FPQ | 127930 | NIE | TAK | WP podcast_show (jest: brak, ma być: prawy-biblijny), WP kategorie (jest: brak, ma być: Biblia) |
| 16.10 | _gZsIsYhVzk | 127935 | NIE | TAK | WP podcast_show (jest: brak, ma być: prawy-biblijny), WP kategorie (jest: brak, ma być: Biblia) |
| 17.10 | ScRgfXz4PMk | 127940 | NIE | TAK | WP podcast_show (jest: brak, ma być: prawy-biblijny), WP kategorie (jest: brak, ma być: Biblia) |

Wykryto również puste szkice (ID: 127835, 127762, 127520). Brak duplikatów dla sprawdzanych tytułów.

## 3. Zamknięte
- Dostęp do GitHub naprawiony (push tylko szablonem z http.extraheader; GCM i gh nie działają; token w D:\Biblioteki\!_sejf\gitrepo.txt — bez wpisywania wartości).
- Ustawienia Antigravity dla media-dispatch zaktualizowane (Security Preset Custom, Terminal Command Auto Execution Always Proceed, file access Allow, sandbox wyłączony).

## 4. Otwarte
- Wpisy WP batcha 04–10.10 (127477–127507) NIE mają `podcast_show` ani meta `podcast_youtube_url`. Wpis 127477 bez kategorii `Biblia`.
- YT h2ncQhExDw4 ma `defaultAudioLanguage=en-US`. **UWAGA:** Użytkownik kazał NIE DOTYKAĆ tego tygodnia, naprawa tylko na jego jawne polecenie (gotowy plik `patch.oct04-10.json` + flaga `--patch-meta --ids-file --execute`).
- Duplikat OsNlnRD0fKk (unlisted, bez wpisu WP) – nie usuwać bez decyzji.
- `mcp_config` GitHub MCP: token zaktualizowany, ale serwer MCP wymaga restartu.
- Uszkodzone pliki projektów w `C:\Users\tomas2\.gemini\config\projects` – 10 plików odzyskanych z domyślnymi.
- Klucze Perplexity i Google Dev Knowledge zostały wyświetlone w logu sesji – rozważyć rotację.

## 5. Lekcje do konstytucji
- Raporty buildera bywają niewiarygodne (fałszywe "5 passed", "brak" w sekcji NIE ZROBIONE) — zawsze wymagany niezależny audyt i weryfikacja po zapisie.
- "Pierwszy token z bazy" = zły kanał. Tokenów należy szukać specyficznie dla danego kanału.
- VSE inject wymaga `schema_data` bez zagnieżdżenia.
- WP-CLI wymaga `--allow-root` i skryptów zamiast komend inline.
- Whisper fallback stosować tylko wtedy, gdy brak oryginalnych napisów.

## 6. Następne kroki
- Oczekujemy na polecenie naprawy starszego batcha lub zatwierdzenie fixów na batchu 11-17.10.
- Rotacja kluczy wymienionych w logach.
