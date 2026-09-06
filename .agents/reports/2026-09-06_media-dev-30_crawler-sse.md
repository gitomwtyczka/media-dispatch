# Raport: Architektura Radarowa (Crawler + Publisher Fix)
**Data:** 2026-09-06
**Callsign:** media-dev-30
**Status:** Zakończono z sukcesem ✅

## Wykonane kroki:
1. **Dostosowanie Crawlera (Zadanie 1)**
   - W skrypcie `agents/kurier365-worker/worker.py` przeprojektowano funkcję `write_candidates_to_sheets` oraz zmieniono domyślny arkusz.
   - Skrypt teraz wysyła zebrane z feedów pozycje bezpośrednio do arkusza `1zqwvS784EaZh1EJIcXk1DliAau1r4X15ENFJjloDSaM` (zakładka `Propozycje Radar`).
   - Układ dodawanych wierszy został dostosowany do nowej specyfikacji z ośmioma kolumnami (m.in. Temat, Źródło, Link, Data opublikowania, ze statusem "Nowa Propozycja").

2. **Naprawa strumienia SSE (Zadanie 2)**
   - Zmodyfikowano kod `agents/radar-worker/radar_sheets_sync.py` przywracając odczyt Server-Sent Events z generatora PressAI.
   - Skrypt prawidłowo iteruje po wynikach z API przy użyciu `iter_lines()`, odcina przedrostek `data: `, parsuje zawartość przy pomocy `json.loads` i na końcu wyciąga z niego tekst korzystając z wyznaczonej ścieżki: `get('result', {}).get('generated_article', '')`.

3. **Wdrożenie:**
   - Poprawione skrypty (`radar_sheets_sync.py` oraz `worker.py`) powędrowały wprost na serwer za pomocą SCP (nadpisując stare wersje w systemie crona).
   - Kod na lokalnej stacji roboczej został skomitowany i prawidłowo zsynchronizowany ze zdalnym `main`.