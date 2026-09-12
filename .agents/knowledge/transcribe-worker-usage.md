# transcribe-worker — Karta Użytku

> Źródło prawdy: ten plik. Zawsze aktualne. | Ostatnia aktualizacja: 12.09.2026

---

## TL;DR dla agenta

- `transcribe.py` — działa **lokalnie na PC** użytkownika (GPU RTX 4060, CUDA)
- **NIE działa na VPS** — nie ma tam GPU
- Uruchamiasz przez `run_command` na lokalnym PC
- Plik: `C:\Users\tomas2\.gemini\antigravity\playground\media-dispatch\transcribe.py`
- Python: zawsze `py -3.12` — nie `python`, nie `py -3.14` (deadlock CUDA!)

---

## Komendy

```powershell
# Podstawowa transkrypcja PL
py -3.12 transcribe.py "D:\Biblioteki\prawy video\plik.mp3"

# + plain text dla PressAI / Stygmat
py -3.12 transcribe.py "plik.mp3" --extract-text

# Z podpowiedziami (nazwiska, terminy — poprawia jakość)
py -3.12 transcribe.py "plik.mp3" --prompt "Wołyńska, Solidarność, PRL"

# PL + EN jednocześnie
py -3.12 transcribe.py "plik.mp3" --dual

# Tylko angielski
py -3.12 transcribe.py "plik.mp3" --translate

# Cały katalog (batch)
py -3.12 transcribe.py "D:\Biblioteki\prawy video\09.2026\\"

# Pełny stack: PL+EN + tekst
py -3.12 transcribe.py "plik.mp3" --dual --extract-text --prompt "[nazwy]"
```

---

## Pliki wyjściowe

| Flaga | Plik | Zastosowanie |
|-------|------|--------------|
| *(brak)* | `plik.pl.srt` | Napisy YouTube |
| `--extract-text` | `plik.pl.srt` + `plik.pl.txt` | Tekst dla PressAI / Stygmat |
| `--dual` | `plik.pl.srt` + `plik.en.srt` | Napisy dwujęzyczne YT |
| `--dual --extract-text` | `.pl.srt` + `.pl.txt` + `.en.srt` + `.en.txt` | Pełny stack |
| `--translate` | `plik.en.srt` | Tylko EN |

Pliki zapisywane **w tym samym katalogu co plik audio**.

---

## Modele

| Model | Szybkość | Jakość | Kiedy użyć |
|-------|----------|--------|-------------|
| `turbo` | ⚡ ~8 min / 60 min audio | dobra | **default** — zawsze zaczynaj od tego |
| `large-v3` | ~25 min / 60 min | najlepsza | trudny materiał, wiele nazwisk |
| `large-v2` | ~20 min / 60 min | dobra | auto-fallback dla `--translate`/`--dual` |
| `large-v1` | ~20 min | średnia | rzadko |
| `small` / `base` | bardzo szybki | słaba | testy/prototypy |

> `turbo` NIE obsługuje `--translate` — skrypt automatycznie przełącza na `large-v2`

---

## Pipeline: audio → artykuł (PressAI)

```
audio.mp3
  → py -3.12 transcribe.py "plik.mp3" --extract-text
  → plik.pl.srt  (napisy YT)
  → plik.pl.txt  (czysty tekst)
  → pressai-worker (input: source_text z .pl.txt)
  → WP draft na kurier365.pl / prawy.pl
```

---

## Pipeline: audio → napisy YT

```
audio.mp3
  → py -3.12 transcribe.py "plik.mp3" [--dual]
  → plik.pl.srt
  → prawy-youtube-worker: captions.insert() przez YT API
  → napisy na kanale YouTube
```

---

## Pipeline: audio → Stygmat (kontekstowe zdjęcia)

```
audio.mp3
  → py -3.12 transcribe.py "plik.mp3" --extract-text
  → plik.pl.txt
  → Stygmat plugin (repo: sonic-void) — rozkłada zdjęcia kontekstowo
  → artykuł WP z automatycznie dobranymi zdjęciami
```

> Stygmat jest rozwijany w `sonic-void`. Po ukończeniu zostanie przeniesiony do `media-dispatch`.

---

## Znane pułapki

| Problem | Przyczyna | Rozwiązanie |
|---------|-----------|-------------|
| `deadlock` / brak wyjścia | Python 3.14 z CUDA | Zawsze `py -3.12` |
| `cublas64_12.dll not found` | PATH bez torch/lib | Skrypt sam to naprawia przy starcie |
| Brak języka / zły | Brak `--prompt` | Dodaj nazwiska i kontekst przez `--prompt` |
| Segment za długi | Duże pauzy | VAD 800ms — już skonfigurowany optymalnie |
| `large-v2` zamiast `turbo` | `--translate`/`--dual` | Celowe — turbo nie obsługuje translate |

---

## Lokalizacja plików w repo

```
media-dispatch/
  transcribe.py                    ← główny skrypt (kórzeń repo)
  agents/transcribe-worker/
    README.md                      ← dokumentacja użytkownika
    constitution.md                ← konstytucja agenta
    usage-card.md                  ← ten plik (skrót dla agentów)
  .agents/knowledge/
    transcribe-worker-usage.md     ← kopia tutaj (auto-ładowana przez agenta)
```

---

*Utworzono: media-strateg | 12.09.2026*
