# Analiza transcribe-worker — zastosowania i usprawnienia

> Callsign: media-analyst-02 | media-dispatch | 11.09.2026  
> Status: raport kompletny

---

## TL;DR

`transcribe.py` to solidny silnik (faster-whisper + VAD + GPU). Obecny stan: skrypt lokalny, uruchamiany ręcznie. Potencjał: rdzeń automatycznego pipeline'u content → SRT → artykuł/YT/Discord → publikacja. Najwyższy priorytet: ekstrakcja plain-text z SRT + integracja z PressAI.

---

## 1. Use Cases — konkretne scenariusze

### A) YouTube workflow: nagranie → SRT → napisy na YT

**Input:** Plik `.mp3` / `.mp4` z nagrania (wywiad, komentarz)  
**Output:** `.pl.srt` + opcjonalnie `.en.srt` → upload do YouTube jako ścieżka napisów

**Jak przyspiesza:** YouTube Data API v3 (`captions.insert`) pozwala uploadować plik SRT przez API. Obecnie redaktor musi ręcznie wgrywać napisy przez YT Studio. Można to wyeliminować całkowicie.

**Implementacja:**
- `transcribe.py` generuje `.pl.srt` i `.en.srt` (tryb `--dual`)
- `youtube-worker` wywołuje `captions.insert` z OAuth tobroz@gmail.com
- Mapowanie: SRT file → `videoId` z VSE DB

**Worker:** rozszerzenie istniejącego `youtube-worker` o moduł `upload_captions()`

**Stopień automatyzacji:** ✅ Pełna automatyzacja możliwa — YouTube API v3 wspiera upload SRT.

---

### B) PressAI integration: transkrypcja wywiadu → artykuł

**Input:** Nagranie wywiadu (30–90 min)  
**Output:** Artykuł prasowy na prawy.pl (draft WP)

**Pipeline:**
```
audio.mp3
  → transcribe.py --model large-v3 --prompt "[nazwiska]"
  → wywiad.pl.srt
  → srt_to_text() [nowa funkcja — plain text bez timestampów]
  → PressAI API (input: tekst wywiadu, prompt: "napisz artykuł z wywiadu")
  → wp-publisher → prawy.pl (status: draft)
```

**Jak przyspiesza:** Wywiad 60 min = transkrypcja ~8 min (GPU turbo) + PressAI ~2 min = artykuł gotowy w 10 min zamiast 2h ręcznej pracy.

**Kluczowa brakująca funkcja:** `srt_to_text()` — ekstrakcja plain-text z pliku SRT (trywialna implementacja, 10 linii kodu).

**Worker:** `pressai-worker` z nowym inputem `audio_file` (obok istniejących `url`, `text`, `mail`).

---

### C) Shorty z transkrypcji — identyfikacja najlepszych cytatów

**Input:** `.pl.srt` z wywiadu/komentarza  
**Output:** Lista top-5 cytatów z timestampami → gotowe markery do cięcia w Premiere

**Pipeline:**
```
wywiad.pl.srt
  → srt_to_text() + zachowanie timestampów
  → LLM prompt: "Znajdź 5 najbardziej uderzających cytatów do shorta (<60s)"
  → Output JSON: [{start, end, text, reason}, ...]
  → Discord #editorial-kurier365 jako embed z przyciskami Approve/Skip
```

**Jak przyspiesza:** Redaktor nie ogląda całego wywiadu — dostaje ready-to-cut markery. Decyzja przez Discord (2 kliknięcia).

**Worker:** nowy `shorts-selector-worker` lub rozszerzenie `redaktor-naczelny` o ten moduł.

**Uwaga:** Upload do TikTok/YT Shorts pozostaje ręczny (z Premiere Pro) zgodnie z obecną architekturą Short Machine. Short-selector dostarcza tylko markery i opisy.

---

### D) SEO z transkrypcji — opisy YT, tagi, meta WP

**Input:** `.pl.srt` (gotowy plik transkrypcji)  
**Output:** Opis YouTube (maks. 5000 znaków), tagi (#10–15), meta description WP

**Pipeline:**
```
wywiad.pl.srt
  → srt_to_text()
  → LLM prompt: "Na podstawie transkrypcji wygeneruj:
       1. Opis YT z słowami kluczowymi i CTA
       2. 12 tagów YT
       3. Meta description WP (160 znaków)"
  → vse-worker: zaktualizuj video w VSE DB (opis, tagi)
  → youtube-worker: videos.update() przez YT API
```

**Jak przyspiesza:** Eliminuje ręczne pisanie opisów — obecnie jeden z najbardziej czasochłonnych kroków workflow YT.

**Worker:** `vse-worker` + `youtube-worker` — oba już istnieją, potrzebują nowego modułu `seo_from_transcript()`.

---

### E) Archiwizacja — baza wiedzy redakcji

**Input:** Wszystkie `.pl.srt` z historycznych nagrań  
**Output:** Pełnotekstowa baza wiedzy (np. Elasticsearch lub prosty folder z `.txt`)

**Zastosowania:**
- Szukanie: "kiedy X mówił o Y?" — instant full-text search po transkryptach
- Kontekst dla nowych artykułów: "znajdź poprzednie wypowiedzi o tym samym temacie"
- Materiał do budowania promptów dla PressAI

**Batch trigger:** `transcribe.py "D:\\Biblioteki\\prawy video\\"` — przetworzy cały katalog. Wyniki `.srt` → konwersja → `.txt` → indeks.

**Worker:** jednorazowy `archive-worker` do backlogu + `vse-worker` do archiwizacji nowych materiałów.

---

### F) Discord Editorial — transkrypt jako draft artykułu

**Input:** Nowe nagranie gotowe do obróbki  
**Output:** Wiadomość Discord w `#editorial-kurier365` z podsumowaniem + przyciskami akcji

**Format wiadomości Discord:**
```
🎙️ Nowy materiał: [tytuł]
Czas: [duration] | Kanał: [Prawy TV / Prawy Biblijny]

📝 Streszczenie (AI):
[3-5 zdań z transkrypcji]

🔑 Kluczowe tematy: [tag1] [tag2] [tag3]

[✅ Generuj artykuł] [✂️ Znajdź cytaty] [📋 Pełny transkrypt] [⏭️ Pomiń]
```

**Jak przyspiesza:** Redaktor widzi streszczenie bez otwierania pliku. Jedno kliknięcie → uruchamia PressAI pipeline.

**Worker:** rozszerzenie `redaktor-naczelny` (już istnieje w architekturze) o obsługę inputu `audio`.

---

## 2. Ulepszenia techniczne transcribe.py

### 2.1 `--extract-text` — plain text z SRT (PRIORYTET #1)

```python
# Dodać do transcribe() po zapisie SRT:
if args.extract_text:
    text_path = output_srt.with_suffix('.txt')
    plain = '\n'.join(sub['text'] for sub in all_segments)
    text_path.write_text(plain, encoding='utf-8')
    print(f'[OK] Plain text: {text_path}')
```

**Wpływ:** 5/5 — blokuje integrację z PressAI  
**Trudność:** 1/5 — trivial, 10 linii kodu  
**Gdzie:** bezpośrednio w `transcribe.py` jako nowa flaga `--extract-text`

---

### 2.2 `--summarize` — automatyczne streszczenie (PRIORYTET #2)

Po transkrypcji wywołanie lokalnego LLM (np. Ollama) lub API (Gemini Flash) z promptem streszczającym.

```
--summarize → .summary.txt (5 zdań + kluczowe tematy)
```

**Wpływ:** 4/5 — input do Discord editorial i PressAI  
**Trudność:** 2/5 — potrzeba API key i jednej funkcji  
**Gdzie:** `transcribe.py` jako opcjonalna flaga (nie bloat gdy nieużywana)

---

### 2.3 `--quotes` — ekstrakcja top-5 cytatów (PRIORYTET #3)

```
--quotes N → .quotes.json [{start, end, text, duration_s}, ...]
```

LLM identyfikuje N najlepszych fragmentów (<60s) na podstawie transkryptu + timestampów z SRT.

**Wpływ:** 4/5 — kluczowe dla Short Machine workflow  
**Trudność:** 2/5 — wywołanie LLM + prosty JSON output  
**Gdzie:** `transcribe.py` lub oddzielny `quotes_extractor.py` w `agents/transcribe-worker/`

---

### 2.4 `--yt-description` — generowanie opisu YouTube (PRIORYTET #4)

```
--yt-description → .yt_meta.json {title, description, tags: [], category_id}
```

LLM generuje kompletne metadane YT z transkrypcji.

**Wpływ:** 5/5 — eliminuje ręczną pracę przy każdym filmie  
**Trudność:** 2/5 — LLM prompt + JSON output  
**Gdzie:** Może być osobny skrypt `yt_meta_from_transcript.py` — lepszy separation of concerns

---

### 2.5 Speaker Diarization — kto mówi (PRIORYTET #5)

Integracja z `pyannote.audio` lub `WhisperX` do detekcji głośników.

```
[PROWADZĄCY 00:01:23] Dzisiaj rozmawiamy o...
[GOŚĆ 00:01:31] Tak, to ważny temat...
```

**Wpływ:** 3/5 — przydatne dla PressAI (lepsza jakość artykułu z wywiadu)  
**Trudność:** 4/5 — wymaga pyannote (HuggingFace token), dodatkowe zależności, setup GPU  
**Gdzie:** Oddzielny skrypt lub opcja w transcribe.py — ze względu na złożoność setup NIE w głównym pliku  
**Uwaga:** Odłożyć na późniejszy etap — niska wartość vs. trudność.

---

## 3. Macierz priorytetów

| # | Ulepszenie | Wpływ (1-5) | Trudność (1-5) | Score | Gdzie | Następny krok |
|---|-----------|------------|---------------|-------|-------|---------------|
| 1 | `--extract-text` (plain text z SRT) | 5 | 1 | ⭐⭐⭐⭐⭐ | `transcribe.py` | Dispatch media-dev: 30 min pracy |
| 2 | YouTube captions upload (SRT → YT API) | 5 | 2 | ⭐⭐⭐⭐⭐ | `youtube-worker` | Potrzeba YT API scope `youtube.force-ssl` |
| 3 | `--summarize` (streszczenie AI) | 4 | 2 | ⭐⭐⭐⭐ | `transcribe.py` | Gemini Flash API key już w env |
| 4 | SEO z transkrypcji (`--yt-description`) | 5 | 2 | ⭐⭐⭐⭐ | nowy skrypt | Blokuje: automatyczny opis YT |
| 5 | PressAI pipeline (audio → artykuł) | 5 | 3 | ⭐⭐⭐⭐ | `pressai-worker` | Blokuje: `--extract-text` (#1) |
| 6 | `--quotes` (top-5 cytatów) | 4 | 2 | ⭐⭐⭐⭐ | `transcribe.py` | Odblokuje Short Machine |
| 7 | Discord editorial embed | 4 | 3 | ⭐⭐⭐ | `redaktor-naczelny` | Blokuje: #1 + #3 |
| 8 | Archiwizacja (batch → baza txt) | 3 | 1 | ⭐⭐⭐ | jednorazowy skrypt | Wartość rośnie z czasem |
| 9 | Speaker Diarization | 3 | 4 | ⭐⭐ | oddzielny skrypt | Odłożyć na v2 |

---

## 4. Rekomendowany plan implementacji

### Faza 1 — Quick wins (1-2 sesje media-dev)

1. **`--extract-text` w transcribe.py** — 30 min, odblokuje wszystko inne
2. **`--summarize` w transcribe.py** — 1h, odblokuje Discord editorial i PressAI
3. **`--quotes` w transcribe.py** — 1h, odblokuje Short Machine markers

Razem: transcribe.py staje się kompletnym pipeline'em preprodukcji.

### Faza 2 — Integracje (3-5 sesji media-dev)

4. **PressAI pipeline** — pressai-worker + nowy input `audio_file`
5. **YouTube captions upload** — youtube-worker + `captions.insert()`
6. **`--yt-description`** — skrypt YT SEO z transkrypcji

### Faza 3 — Editorial automation (5+ sesji)

7. **Discord editorial embed** — redaktor-naczelny + audio input handler
8. **Archiwizacja backlog** — jednorazowy batch run + indeks tekstowy

---

## 5. Wnioski dla media-strateg

1. **transcribe.py jest gotowy produkcyjnie** — stabilny, GPU, VAD, batch. Nie wymaga przepisywania.

2. **Brakuje jednej funkcji blokującej cały pipeline:** `srt_to_text()`. To 10 linii kodu. Dispatch media-dev już dziś.

3. **Największy ROI:** YouTube captions upload przez API — eliminuje 100% ręcznej pracy przy napisach (każdy film = oszczędność 5-10 min).

4. **PressAI + audio = killer feature** — wywiad 60 min → artykuł w 10 min. Priorytet po odblokowaniu #1.

5. **Speaker diarization odłożyć** — złożoność nieproporcjonalna do wartości na tym etapie.

---

*media-analyst-02 | media-dispatch | 11.09.2026 | raport kompletny*
