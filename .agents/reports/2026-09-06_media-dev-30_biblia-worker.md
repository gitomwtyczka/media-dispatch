# Raport: Biblia Worker (Recovery & Sync)
Callsign: media-dev-30
Data: 2026-09-06

## Wykonane zadania:
1. **Recovery Batch (09.09 - 12.09)**:
   - Naprawiono bug `pub_at_local` -> `pub_at` w skrypcie `biblia_batch_sept.py`.
   - Dodano konwersję strefy czasowej do ISO 8601 UTC przy insercie do API YouTube (`publishAt`).
   - Wdrożono warunek dla środy (`09.09`) pomijający ponowny inject WP (`step4`), by nie duplikować posta.
   - Pomyślnie uruchomiono skrypt. Skrypt przeanalizował 4 wpisy, zaktualizował YT i playlisty, a także utworzył odpowiednie posty na WP dla czwartku, piątku i soboty.
   
2. **Docelowy Worker (`biblia_sheets_sync.py`)**:
   - Utworzono docelowy skrypt w `agents/biblia-worker/biblia_sheets_sync.py`.
   - Worker łączy się z arkuszem `Biblia` za pomocą Service Account.
   - Automatycznie rozpoznaje wpisy bez flagi "Opublikowane" i posiadające link do YouTube.
   - Ekstrahuje `videoId` z linków YT, parsuje datę z kolumny "emisja", konwertuje na UTC.
   - Uruchamia standardowy pipeline (Whisper, VTT, VSE Generate, WP Inject, YT SEO, Playlist).
   - Oznacza wiersz statusem "Opublikowane" w kolumnie L (12).

## Uwagi:
Pliki wciąż znajdują się lokalnie na instancji, jako że był to skrypt testowy/untracked. Oczekują na commita (autoryzacja MCP lub gh).