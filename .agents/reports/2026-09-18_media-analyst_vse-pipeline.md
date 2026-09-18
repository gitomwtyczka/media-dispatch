# VSE Pipeline — Analiza najnowszych skutecznych uruchomień | 18.09.2026

## TL;DR
Skrypty VSE Pipeline korzystają z konta YouTube `4b97ab0c-98ee-46c6-9be8-d86adc4cb38a` (tobroz@gmail.com). Główne uruchomienia (np. z 15.09) obsługiwały wpisy na Prawy.pl, poprawnie generując SEO i aktualizując YouTube'a z tokenem generowanym bezpośrednio w kontenerze `vse-api`. Produkcyjny worker `prawy-studio-worker` sprawdza najpierw dostępność napisów, by uniknąć halucynacji.

## Najnowszy skuteczny skrypt
- Brain sesja: `6aca8d11-0716-4ec4-8bb0-6608a2d223ae` (2026-09-15)
- Plik: `prawy_full_flow_v2.py`
- VIDEO_ID: `EWkRL1sEqQE` (Wółyń), `s6qif3Ed57E` (Pietrzak)
- Kluczowe parametry: 
  - `portal_id`: `2b047d7d-15a1-4d2f-8463-f89c2275bb73`
  - Token YT sub: `4b97ab0c-98ee-46c6-9be8-d86adc4cb38a`
  - Kanał `channel_ids` z DB: pobierane dynamicznie (`SELECT id FROM youtube_channels WHERE is_active=true;`)
- Co działało: Aktualizacja opisu na YT (Wółyń) i wstrzykiwanie nowego artykułu (Pietrzak), sprawdzanie napisów przed startem.

## Prawy Studio Worker — produkcyjne parametry
- Używa `PORTAL_ID = "2b047d7d-15a1-4d2f-8463-f89c2275bb73"` i `YT_CHANNEL_ID = "UCoH2G9By4OX3kcLsc8lHgDw"`.
- Zawsze ustawia `DEFAULT_WP_STATUS = "draft"` i `DEFAULT_YT_STATUS = "unlisted"`.
- Lokalnie video pobiera z `C:\Users\tomas2\Videos\Prawy` wyszukując wg wzorca `*{youtube_id}*`.
- Krok-po-kroku checkpointuje stan przetwarzania do `batch_progress.json`.

## Halwa Leo i Halwa Wójcik 2 — stan w VSE
- Czy są w bazie: Nie / Brak na liście
- YouTube ID (jeśli znany): Nieznany z VSE API (ostatnie 100 wyników).
- Status w VSE: Brak w historii zleceń — system nie posiada tabeli `videos` dla bezpośrednich rekordów, a API nie zwraca nic z "halwa/leo/wójcik" w nagłówku.

## Gotowe parametry dla workera
```python
VIDEO_1 = {"url": "https://www.youtube.com/watch?v=...", "id": "...", "local_path": r"C:\Users\tomas2\Videos\Prawy\..."}
VIDEO_2 = {"url": "https://www.youtube.com/watch?v=...", "id": "...", "local_path": r"C:\Users\tomas2\Videos\Prawy\..."}
PORTAL_ID = "2b047d7d-15a1-4d2f-8463-f89c2275bb73"
CHANNEL_ID = "UCoH2G9By4OX3kcLsc8lHgDw"
USER_ID = "4b97ab0c-98ee-46c6-9be8-d86adc4cb38a"
```

## Blokery / ostrzeżenia
⚠️ Worker musi bezwzględnie sprawdzić czy dla danego wideo są wygenerowane napisy (`check_captions_only: True`), w przeciwnym razie wygenerowany artykuł będzie oparty na halucynacji LLM z powodu braku transkryptu (potwierdzone w teście Pietrzak z 15.09). Dodatkowo z powodu uciążliwości wywołań w Bash z uciekaniem znaków — worker powinien przygotować lokalnie self-contained python script i odpalać go asynchronicznie przez SSH, podobnie jak `worker.py`.

## Rekomendacja
Rekomenduję natychmiastowe uruchomienie `prawy-studio-worker` podając mu JSON z brakującymi `youtube_id` Halwa/Leo, ponieważ sam sprawnie poradzi sobie z generacją draftu dla WordPressa oraz wideo dla YT (dopóki pliki fizyczne znajdują się w `C:\Users\tomas2\Videos\Prawy`). Zanim worker zacznie pracę, sprawdź czy fizycznie wgrano tam pliki mp4.
