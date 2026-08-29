# vse-worker / scripts

Skrypty implementujące pipeline VSE dla kanału Prawy Biblijny.

## biblia_full_pipeline.py — PRAWIDŁOWY flow (od 30.08.2026)

Prawidłowy flow dla kanału bez auto-napisów YouTube:

```
MP3 → Whisper (/v1/audio/generate) → VTT
  → captions.insert (napisy na YT)
  → /v1/generate z URL YouTube (thumbnail ✅, VideoObject ✅, embed ✅)
  → /v1/inject → WP post zaplanowany
```

**Błąd z 29.08.2026:** użycie `/v1/audio/generate` end-to-end → brak thumbnail i VideoObject schema.
**Zasada:** audio pipeline = TYLKO transkrypcja. Pipeline SEO zawsze przez YouTube URL.

### Konfiguracja
1. Wygeneruj token VSE: patrz `.agents/knowledge/vse-worker-constitution.md` sekcja 2
2. Pobierz YT access_token: `GET https://vse.impresjapr.pl/v1/youtube/channels`
3. Uzupełnij CONFIG w skrypcie
4. Uruchom: `python biblia_full_pipeline.py`

### Zależności
```bash
pip install requests
```