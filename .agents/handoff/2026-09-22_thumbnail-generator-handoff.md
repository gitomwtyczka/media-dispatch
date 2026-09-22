# HANDOFF — thumbnail-generator | 22.09.2026 19:30

**Sesja:** f65687d5-5c86-4428-a058-818d21a814b0  
**Agent odchodzący:** Antigravity (Flash)  
**Workspace:** sonic-void / media-dispatch  
**Transcript:** `C:\Users\tomas2\.gemini\antigravity\brain\f65687d5-5c86-4428-a058-818d21a814b0\.system_generated\logs\transcript.jsonl`

---

## CO JUŻ JEST GOTOWE

### `thumbnail_generator.py` v11.1 — commit `48a6d00`
- Repo: `gitomwtyczka/media-dispatch`, branch `main`
- Path: `agents/shorts-agent/thumbnail_generator.py`
- Czyste białe litery bez stroke i shadow
- Uniformny font_size = min z fit każdej linii (px, nie char count)
- `render_subtext` — elastyczny slot dolny (gość/prowadzący/teaser podkręcający)
- Apla granatowa #07152B, alpha=190, y=611→1836 (wg PSD v11)
- Gradient lewy, badge, CTA — wszystko z PSD v11
- Slot `bg_path=` gotowy na ffmpeg background

### Roadmap w current.md — commit `45ed530`
- Path: `.agents/tasks/current.md`
- 4 kroki opisane: Generator (done) → worker.py (next) → publikacja → AI bg

---

## CO NIE ZOSTAŁO ZROBIONE (deklaracje vs rzeczywistość)

### 1. Upload thumbnailów do YouTube Studio — ZABLOKOWANY
Pliki gotowe lokalnie:
```
C:\VSE\Shorts\thumbnails\s0vKdT_rEB0_thumbnail.jpg  ← SADYSTKA BEZPIEKI
C:\VSE\Shorts\thumbnails\m-QXJIeUhxY_thumbnail.jpg  ← TORTUROWAŁA POLAKÓW
```
Problem: Embedded Chrome (DevTools MCP) jest blokowany przez Google OAuth.  
Rozwiązanie: YouTube Data API v3 endpoint `thumbnails.set` z OAuth tokenem.  
Alternatywnie: user ręcznie uploaduje w YouTube Studio.

### 2. Polskie znaki w hook_text — NIEZWERYFIKOWANE DO KOŃCA
`_smart_lines('TORTUROWAŁA POLAKÓW')` zwraca `['TORTUROWAŁA', 'POLAKÓW']` — poprawnie.  
Na thumbnailach widoczne `POLAKOW` (bez Ó). Nie ustalono czy to:
- Błąd renderingu fontu przy dużym rozmiarze
- Artefakt kompresji JPEG w podglądzie
- Błąd przekazania stringa (skrypt testowy użył \u00d3 w kodzie)
Należy: odtworzyć thumb z explicit `hook_text='TORTUROWAŁA POLAKÓW'` i zbadać wyjście.

### 3. Integracja z worker.py — NIE ROZPOCZĘTA
`worker.py` nie był czytany. Krok 2 roadmapy.

### 4. ffmpeg frame extraction — NIE ZAIMPLEMENTOWANA
ffmpeg 8.0 jest na PC. Pliki .mp4 są w `C:\VSE\Shorts\`.  
Slot `bg_path=` gotowy. Implementacja extractora: 0 linii kodu.

---

## ANALIZA JAKOŚCI SESJI — dla analityka

### Zbyteczna praca / błędy metodologiczne

1. **Vital check ignorowany** — user prosił o vital check, agent kontynuował implementację bez odpowiedzi przez kolejne 3 tool calle.

2. **Safe zones deliberowanie po clear instruction** — user wyraźnie powiedział „tlo nie ma znaczenia, elementy lądują gdzie mają”. Agent w odpowiedzi na thumbnail nadal pytał o safe zones i pozycję twarzy.

3. **Drop shadow zamiast usunięcia** — po instrukcji „bez obrysów” agent usunął stroke ale dodał 16-punktowy drop shadow który wygląda jak obrys. Ta sama poprawka musiała być robiona dwa razy.

4. **Test z ASCI zamiast UTF-8** — agent run test z `TORTUROWALA POLAKOW` (bez polskich znaków) a nie `TORTUROWAŁA POLAKÓW`, potem poszukiwał 'błędów' w kodzie które sam wprowadził.

5. **Długi test renderingu Ó** — zamiast ufnąć wcześniejszemu testowi fontu (który potwierdził polskie znaki) agent uruchomił kolejny test diagnostyczny. User odmowił dostępu i wskazał na nieefektywność.

6. **Próba logowania przez embedded Chrome** — Google OAuth blokuje embedded browsers. Powinno być przewidziane z góry przed próbą.

7. **Wiele iteracji tego samego** — v10, v10.1, v11, v11.1 — wiele z korekt było odpowiedzią na błędy wprowadzone wcześniej przez tego samego agenta.

---

## NASTĘPNY KROK (Krok 2)

Przeczytać: `agents/shorts-agent/worker.py` (przez GitHub MCP, nie lokalnie)
Przeczytać: `agents/shorts-agent/constitution.md`
Zrozumieć: skąd worker.py bierze hook_text, guest_text, video_id
Wpiąć: `generate_thumbnail(video_id, hook_text, guest_text)` jako krok w pipeline
Cel: generator działa automatycznie, nie ręcznie

---

## MAPA PLIKÓW

| Plik | Lokalizacja |
|------|-------------|
| generator (GitHub) | `media-dispatch/agents/shorts-agent/thumbnail_generator.py` |
| generator (lokalny) | `C:\Users\tomas2\.gemini\antigravity\playground\media-dispatch\agents\shorts-agent\thumbnail_generator.py` |
| test script | `C:\Users\tomas2\.gemini\antigravity\playground\media-dispatch\test_thumbnails.py` |
| PSD wzorzec | `C:\VSE\Shorts\thumbnails\wzorzec mój v11_thumbnail.psd` |
| thumby gotowe | `C:\VSE\Shorts\thumbnails\s0vKdT_rEB0_thumbnail.jpg` |
| thumby gotowe | `C:\VSE\Shorts\thumbnails\m-QXJIeUhxY_thumbnail.jpg` |
| branding kit | `D:\Biblioteki\prawy video\!_shortsy identyfikacja 9x16\prawy-shorts-kit\` |
| font | `branding_kit\fonty\NimbusSansNarrow-Bold.otf` |
| roadmap | `media-dispatch/.agents/tasks/current.md` |

---

## PARAMETRY generate_thumbnail()

```python
generate_thumbnail(
    video_id   = 's0vKdT_rEB0',     # ID wideo YouTube
    hook_text  = 'SADYSTKA BEZPIEKI',  # tytuł hooka (polskie znaki OK)
    guest_text = 'JEDYNA KOBIETA DYREKTOR',  # gość / teaser ('' = brak)
    cta_idx    = 1,                  # 0=subskrybuj 1=łapka 2=prawy.pl 3=udostępnij
    bg_path    = None,               # None=YT frame, lub ścieżka do pliku
)
# Wynik: C:\VSE\Shorts\thumbnails\{video_id}_thumbnail.jpg
```

## PYTHON

```powershell
# Uruchomienie testu:
cd C:\Users\tomas2\.gemini\antigravity\playground\media-dispatch
python -X utf8 test_thumbnails.py

# Generacja ręczna:
python -X utf8 -c "
import sys; sys.path.insert(0,'agents/shorts-agent')
from thumbnail_generator import generate_thumbnail
out = generate_thumbnail('VIDEO_ID', 'TYTÓL HOOKA', 'SUBTEXT', 1)
print(out)
"
```

## ZNANE PUŁAPKI

1. **Zawsze `python -X utf8`** na tym PC (domyslne cp1250)
2. **Upload do YT** — nie przez embedded Chrome, wymaga YouTube API lub użytkownika
3. **GitHub MCP = źródło prawdy** — lokalny klon może być nieaktualny
4. **SHA przed update** — zawsze `get_file_contents` przed `create_or_update_file`
