# transcribe-worker
**Warstwa:** Production (Warstwa 3)  
**Callsign:** transcribe-worker  
**Stack:** Python 3.12 · faster-whisper 1.2.1 · CUDA 12.4 · RTX 4060

## Cel agenta

Automatyczna transkrypcja i tłumaczenie plików audio do formatu SRT.
Obsługuje pojedyncze pliki i całe katalogi. Generuje napisy gotowe do:
- uploadu na YouTube
- ekstrakcji tekstu dla PressAI (artykuły z wywiadów)
- archiwizacji treści redakcyjnych

## Uruchomienie

### Wymagania
- Python 3.12 (`py -3.12`)
- GPU NVIDIA z CUDA 12.x (lub `--cpu` fallback)
- Zainstalowane zależności: `py -3.12 -m pip install faster-whisper`

### Podstawowe użycie

```powershell
# Transkrypcja pojedynczego pliku (model domyślny: turbo)
py -3.12 transcribe.py plik.mp3

# Wybór modelu
py -3.12 transcribe.py plik.mp3 --model large-v3

# Wymuszenie języka (domyślnie: pl)
py -3.12 transcribe.py plik.mp3 --language pl

# Prompt redukujący halucynacje
py -3.12 transcribe.py plik.mp3 --prompt "Nawrocki, Bosak, Konfederacja, PRL"

# Tłumaczenie na angielski
py -3.12 transcribe.py plik.mp3 --translate

# Dual output: PL + EN jednocześnie
py -3.12 transcribe.py plik.mp3 --dual

# CPU fallback (bez GPU)
py -3.12 transcribe.py plik.mp3 --cpu

# Batch — cały katalog
py -3.12 transcribe.py D:\nagrania\

# Batch dual — cały katalog, PL + EN
py -3.12 transcribe.py D:\nagrania\ --dual

# Kombinacja flag
py -3.12 transcribe.py plik.mp3 --model large-v3 --language pl --prompt "Konfederacja, Bosak" --dual
```

## Modele

| Model | Szybkość | Jakość | Użycie |
|-------|----------|--------|--------|
| turbo | ⚡⚡⚡ | ★★★★☆ | Standardowe nagrania studyjne |
| large-v3 | ⚡ | ★★★★★ | Słabe audio, wiele nazwisk własnych |
| large-v2 | ⚡ | ★★★★★ | --translate (tłumaczenie EN) |
| small | ⚡⚡⚡⚡ | ★★☆☆☆ | Test/szybki draft |

## Tryby pracy

| Tryb | Komenda | Output |
|------|---------|--------|
| Transkrypcja PL | `transcribe.py plik.mp3` | `plik.pl.srt` |
| Tłumaczenie EN | `transcribe.py plik.mp3 --translate` | `plik.en.srt` |
| Dual PL+EN | `transcribe.py plik.mp3 --dual` | `plik.pl.srt` + `plik.en.srt` |
| Batch katalog | `transcribe.py D:\katalog\` | wszystkie pliki |
| Batch dual | `transcribe.py D:\katalog\ --dual` | wszystkie pliki × 2 |

## Obsługiwane formaty wejścia

`.mp3` `.wav` `.m4a` `.mp4` `.wmv` `.wma` `.flac` `.ogg` `.aac` `.opus`

## Parametry VAD (polskie studio)

Skrypt jest skonfigurowany pod polską mowę w studio:
- `min_silence_duration_ms=800` — dłuższe pauzy retoryczne
- `threshold=0.5` — standardowa czułość
- `speech_pad_ms=300` — ochrona końców słów

## Wskazówki dla redakcji

### --prompt (redukcja halucynacji)
Przy nagraniach z nazwiskami zawsze dodawaj prompt:
```powershell
--prompt "Nawrocki, Bosak, Konfederacja, PRL, Młodzież Wszechpolska"
```

### Słabe audio
Użyj `--model large-v3` — drastycznie lepsza odporność na szumy.

### Szybki podgląd (draft)
Użyj `--model small` — 4x szybciej, niższa dokładność.

## Znane ograniczenia

- `--translate` używa modelu `large-v2` (auto-fallback z turbo)
- Whisper tłumaczy wyłącznie na angielski (architektura modelu)
- Pierwsze uruchomienie pobiera model z HuggingFace (~1-3 GB)
- Segmenty są max 3s / 42 znaki (standard YouTube TV)
- Segmenty min 0.8s (czytelność dla oka)

## Integracja z pipeline

```
audio → transcribe-worker → .pl.srt → YouTube upload
                          → .en.srt → YouTube upload (EN subtitles)
                          → .pl.srt → pressai-worker (artykuł z wywiadu)
```

## Historia

| Data | Zmiana |
|------|--------|
| 11.09.2026 | Inicjacja — handoff od local-guardian |
| 11.09.2026 | faster-whisper + VAD + CUDA |
| 11.09.2026 | Word-level split (max 3s/42 chars) |
| 11.09.2026 | --translate + --dual (PL+EN) |
| 11.09.2026 | --prompt CLI + VAD 800ms |
| 11.09.2026 | Batch directory mode + language suffixes |
