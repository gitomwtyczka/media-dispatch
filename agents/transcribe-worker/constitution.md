# transcribe-worker — Konstytucja

> Plik dla agentów AI które wywołują transcribe-worker.  
> Ostatnia aktualizacja: 11.09.2026 | media-dev-37

---

## 1. Tożsamość

| Pole | Wartość |
|------|--------|
| **Callsign** | `transcribe-worker` |
| **Warstwa** | Production (Warstwa 3) |
| **Stack** | Python 3.12 · faster-whisper 1.2.1 · CUDA 12.4 · RTX 4060 |
| **Środowisko** | Lokalny PC z GPU (nie VPS!) |
| **Skrypt** | `agents/transcribe-worker/transcribe.py` |

---

## 2. Jak wywołać

### Składnia bazowa

```powershell
py -3.12 transcribe.py <ŚcIEŻKA_DO_PLIKU_LUB_KATALOGU> [flagi]
```

### Flagi

| Flaga | Typ | Domyślnie | Opis |
|-------|-----|----------|------|
| `--model` | str | `turbo` | Model Whisper: `turbo`, `large-v3`, `large-v2`, `small` |
| `--language` | str | `pl` | Język źródłowy audio |
| `--prompt` | str | `""` | Initial prompt — redukuje halucynacje |
| `--translate` | flag | off | Tłumaczenie na angielski (output: `.en.srt`) |
| `--dual` | flag | off | Generuje oba: `.pl.srt` + `.en.srt` |
| `--cpu` | flag | off | CPU fallback (bez CUDA) |

### Przykłady gotowych komend

```powershell
# Standard — studyjne nagranie PL
py -3.12 transcribe.py "D:\nagrania\wywiad.mp3"
# Output: wywiad.pl.srt

# Z promptem (nazwy własne)
py -3.12 transcribe.py "D:\nagrania\debata.mp3" --prompt "Nawrocki, Bosak, Konfederacja"

# Dual PL+EN (YouTube upload)
py -3.12 transcribe.py "D:\nagrania\wywiad.mp3" --dual
# Output: wywiad.pl.srt + wywiad.en.srt

# Słabe audio (konferencja, telefon)
py -3.12 transcribe.py "D:\nagrania\slabe.mp3" --model large-v3

# Batch — cały katalog, dual
py -3.12 transcribe.py "D:\odcinki\" --dual

# CPU fallback
py -3.12 transcribe.py "D:\nagrania\plik.mp3" --cpu
```

---

## 3. Format output

```
<nazwa_pliku>.<język>.srt
```

Przykłady:
- `wywiad.pl.srt` — transkrypcja polska
- `wywiad.en.srt` — tłumaczenie angielskie
- `2026-09-10_debata.pl.srt` — z prefiksem daty

SRT jest zapisywany obok pliku źródłowego.

---

## 4. Parametry segmentacji (wbudowane)

| Parametr | Wartość | Powod |
|----------|---------|-------|
| Max czas segmentu | 3.0s | Standard YouTube TV |
| Max znaki segmentu | 42 | Czytelność na TV |
| Min czas segmentu | 0.8s | Czytelność dla oka |
| VAD min_silence | 800ms | Polskie pauzy retoryczne |
| VAD threshold | 0.5 | Standardowa czułość |
| VAD speech_pad | 300ms | Ochrona końców słów |

---

## 5. Integracja z pipeline

```
audio (mp3/wav/mp4/...)
  ↓
transcribe-worker
  ├── .pl.srt → YouTube upload (polskie napisy)
  ├── .en.srt → YouTube upload (angielskie napisy)
  └── .pl.srt → pressai-worker (artykuł z wywiadu)
```

### Obsługiwane formaty wejścia
`.mp3` `.wav` `.m4a` `.mp4` `.wmv` `.wma` `.flac` `.ogg` `.aac` `.opus`

---

## 6. Znane pułapki operacyjne

### P1 — `--translate` wymusza model `large-v2`
Whisper CLI obsługuje tłumaczenie tylko przez `large-v2`. Skrypt automatycznie przełącza model — nie podawaj `--model turbo --translate` oczekując turbo.

### P2 — Whisper tłumaczy wyłącznie na angielski
Architektura modelu. Nie ma opcji tłumaczenia PL→DE, PL→FR etc. Jeśli potrzebujesz innego języka — inny pipeline.

### P3 — Pierwsze uruchomienie pobiera model (~1-3 GB)
Modele są cache'owane lokalnie po pierwszym pobraniu. Jeśli skrypt "wisi" na starcie — czeka na download.

### P4 — ściezki z polskimi znakami
PowerShell może mieć problem z kodowaniem ścieżek zawierających `ń`, `ś`, `ż` etc. Jeśli wystąpi błąd — użyj krótszych ściezek lub przemapuj przez junction.

### P5 — GPU OOM przy `large-v3` + długi plik
Przy bardzo długich plikach (>2h) i modelu `large-v3` może wystąpić OOM na 8GB VRAM. Fallback: `--cpu` lub podziel plik.

### P6 — Batch mode ignoruje nieobsługiwane rozszerzenia
Skrypt cicho pomija pliki z nieobsługiwanym rozszerzeniem. Jeśli plik nie został przetransformowany — sprawdź rozszerzenie.

---

## 7. Raport po zakończeniu

Worker raportuje do rodzica w formacie:

```
[transcribe-worker | 11.09.2026 HH:MM] STATUS

Plik: <ścieżka>
Model: <model>
Output:
  - <plik.pl.srt> — OK / ERROR
  - <plik.en.srt> — OK / ERROR (jeśli --dual)

Czas: Xs
Batch: X plików / Y sukcesów / Z błędów

Następne kroki:
  - [ ] Upload na YouTube
  - [ ] Prześląż do pressai-worker
```

---

## 8. Architektura skryptu

```python
# Lokalizacja: agents/transcribe-worker/transcribe.py
# Uruchamiany lokalnie (PC z GPU), nie na VPS

# Główne moduły:
- faster_whisper.WhisperModel   # model transkrypcji
- faster_whisper.BatchedInferencePipeline  # GPU batch processing
- argparse                      # CLI flags
- pathlib.Path                  # cross-platform paths
- srt (implicit format write)   # SRT output
```

---

*Inicjacja: media-dev-37 | 11.09.2026*
