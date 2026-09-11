#!/usr/bin/env python3
"""
transcribe.py — Automatyczny skrypt transkrypcji audio do SRT
Silnik: faster-whisper + VAD (silero-vad)
GPU: CUDA (RTX 4060)

Użycie:
    py -3.12 transcribe.py "D:\\Biblioteki\\prawy video\\07.09\\plik.mp3"
    py -3.12 transcribe.py "plik.mp3" --model large-v2 --language pl
    py -3.12 transcribe.py "plik.mp3" --cpu   # fallback CPU
    py -3.12 transcribe.py "plik.mp3" --translate  # bezpośrednio do EN
    py -3.12 transcribe.py "plik.mp3" --dual       # PL + EN (dwa przebiegi)
    py -3.12 transcribe.py "plik.mp3" --prompt "Osowski, Płużański, Młodzież Wszechpolska, PRL"

Wyjście: plik .srt w tym samym katalogu co plik wejściowy.
"""

import argparse
import os
import sys

# Fix dla Windows: ctranslate2 szuka cublas64_12.dll w PATH
# PyTorch bundluje tę bibliotekę w swoim katalogu lib
if sys.platform == "win32":
    try:
        import torch
        _torch_lib = os.path.join(os.path.dirname(torch.__file__), "lib")
        if os.path.isdir(_torch_lib):
            os.environ["PATH"] = _torch_lib + os.pathsep + os.environ.get("PATH", "")
            os.add_dll_directory(_torch_lib)
    except (ImportError, OSError):
        pass

from pathlib import Path
from datetime import timedelta


def format_timestamp(seconds: float) -> str:
    """Konwertuje sekundy na format SRT: HH:MM:SS,mmm"""
    total_ms = int(round(seconds * 1000))
    millis = total_ms % 1000
    total_seconds = total_ms // 1000
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def split_segment_by_words(segment, max_duration: float = 3.0, max_chars: int = 42):
    """
    Dzieli długi segment na podsegmenty max max_duration sekund lub max_chars znaków.
    Zwraca listę dict: [{start, end, text}, ...]
    """
    MIN_CHUNK_DURATION = 0.8  # min czas trwania segmentu (oko zdazy przeczytac)
    words = segment.words if segment.words else []

    if not words:
        return [{"start": segment.start, "end": segment.end, "text": segment.text.strip()}]

    chunks = []
    chunk_words = []
    chunk_start = words[0].start
    chunk_chars = 0

    for i, word in enumerate(words):
        word_text = word.word
        chunk_words.append(word)
        chunk_chars += len(word_text)
        duration = word.end - chunk_start

        should_cut = (
            (duration >= max_duration) or
            (chunk_chars >= max_chars and len(chunk_words) > 1)
        ) and duration >= MIN_CHUNK_DURATION

        if should_cut:
            text = "".join(w.word for w in chunk_words).strip()
            if text:
                chunks.append({"start": chunk_start, "end": word.end, "text": text})
            chunk_words = []
            chunk_chars = 0
            if i + 1 < len(words):
                chunk_start = words[i + 1].start

    # Ostatni chunk
    if chunk_words:
        text = "".join(w.word for w in chunk_words).strip()
        if text:
            # Jeśli ostatni chunk jest za krótki, dołącz do poprzedniego
            last_duration = chunk_words[-1].end - chunk_words[0].start
            if last_duration < MIN_CHUNK_DURATION and chunks:
                # Dolącz do ostatniego chunku
                prev = chunks[-1]
                prev_text = prev["text"]
                combined_text = (prev_text + " " + text).strip()
                chunks[-1] = {"start": prev["start"], "end": chunk_words[-1].end, "text": combined_text}
            else:
                chunks.append({"start": chunk_words[0].start, "end": chunk_words[-1].end, "text": text})

    return chunks if chunks else [{"start": segment.start, "end": segment.end, "text": segment.text.strip()}]


def transcribe(audio_path: str, model_size: str, language: str, use_cpu: bool, task: str = "transcribe", output_suffix: str = "", prompt: str = ""):
    from faster_whisper import WhisperModel

    audio_path = Path(audio_path)
    if not audio_path.exists():
        print(f"[ERROR] Plik nie istnieje: {audio_path}")
        sys.exit(1)

    if output_suffix:
        output_srt = audio_path.with_name(audio_path.stem + output_suffix + ".srt")
    else:
        output_srt = audio_path.with_suffix(".srt")

    if use_cpu:
        device = "cpu"
        compute_type = "int8"
        print("[INFO] Tryb CPU (int8)")
    else:
        device = "cuda"
        compute_type = "float16"
        print("[INFO] Tryb GPU CUDA (float16)")

    print(f"[INFO] Model: {model_size}")
    print(f"[INFO] Język: {language}")
    print(f"[INFO] Task: {task}")
    print(f"[INFO] Plik wejściowy: {audio_path}")
    print(f"[INFO] Plik wyjściowy: {output_srt}")
    if prompt:
        print(f"[INFO] Prompt: {prompt}")
    print("[INFO] Ładowanie modelu...")

    model = WhisperModel(model_size, device=device, compute_type=compute_type)

    print("[INFO] Transkrypcja z VAD... (to może chwilę potrwać)")

    segments, info = model.transcribe(
        str(audio_path),
        language=language,
        task=task,
        condition_on_previous_text=False,
        vad_filter=True,
        vad_parameters=dict(
            min_silence_duration_ms=800,   # było 500 — za krótkie dla polskich pauz retorycznych
            threshold=0.5,
            speech_pad_ms=300,              # było 200 — lepsza ochrona końców słów
        ),
        word_timestamps=True,
        beam_size=5,
        initial_prompt=prompt if prompt else None,
    )

    print(f"[INFO] Wykryty język: {info.language} (pewność: {info.language_probability:.1%})")
    print("[INFO] Zapis SRT...")

    srt_blocks = []
    index = 1

    for segment in segments:
        sub_segments = split_segment_by_words(segment, max_duration=3.0, max_chars=42)
        for sub in sub_segments:
            start = format_timestamp(sub["start"])
            end = format_timestamp(sub["end"])
            text = sub["text"]

            if not text:
                continue

            block = f"{index}\n{start} --> {end}\n{text}\n"
            srt_blocks.append(block)
            print(f"  [{start} --> {end}] {text}")
            index += 1

    with open(output_srt, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_blocks))

    print(f"\n[OK] Gotowe! {index - 1} segmentów zapisanych do:")
    print(f"     {output_srt}")


def main():
    parser = argparse.ArgumentParser(
        description="Transkrypcja audio \u2192 SRT (faster-whisper + VAD, GPU CUDA)"
    )
    parser.add_argument("audio", help="Śceżka do pliku audio (.mp3, .wav, .m4a, ...)")
    parser.add_argument(
        "--model", "-m",
        default="turbo",
        choices=["tiny", "base", "small", "medium", "large-v1", "large-v2", "large-v3", "turbo"],
        help="Model Whisper (domyślnie: turbo)"
    )
    parser.add_argument(
        "--language", "-l",
        default="pl",
        help="Kod języka ISO 639-1 (domyślnie: pl)"
    )
    parser.add_argument(
        "--cpu",
        action="store_true",
        help="Wymusz CPU zamiast CUDA (wolniejsze, fallback)"
    )
    parser.add_argument(
        "--translate",
        action="store_true",
        help="Transkrybuj audio bezpośrednio do angielskiego (task=translate)"
    )
    parser.add_argument(
        "--dual",
        action="store_true",
        help="Generuj dwa pliki SRT: .pl.srt (oryginalny) i .en.srt (angielski)"
    )
    parser.add_argument(
        "--prompt", "-p",
        default="",
        help="Wskazówka dla modelu (nazwy własne, kontekst). Np. --prompt \"Osowski, Płużański, Młodzież Wszechpolska, PRL\""
    )

    args = parser.parse_args()

    if "Python314" in sys.executable or "python314" in sys.executable:
        print("[ERROR] Wykryto Python 3.14 \u2014 deadlock z CUDA. Użyj: py -3.12 transcribe.py")
        sys.exit(1)

    # Modele które NIE obsługują task=translate
    TRANSLATE_UNSUPPORTED = {"turbo"}

    if (args.translate or args.dual) and args.model in TRANSLATE_UNSUPPORTED:
        print(f"[WARN] Model '{args.model}' nie obsługuje tłumaczenia (task=translate).")
        print(f"[WARN] Automatycznie przełączam na large-v2 dla tłumaczenia.")
        translate_model = "large-v2"
    else:
        translate_model = args.model

    if args.dual:
        print("[INFO] Tryb DUAL: generowanie PL + EN")
        print("[INFO] --- Przebieg 1/2: język źródłowy ---")
        transcribe(args.audio, args.model, args.language, args.cpu,
                   task="transcribe", output_suffix=".pl", prompt=args.prompt)
        print(f"[INFO] --- Przebieg 2/2: tłumaczenie EN (model: {translate_model}) ---")
        transcribe(args.audio, translate_model, args.language, args.cpu,
                   task="translate", output_suffix=".en", prompt=args.prompt)
    elif args.translate:
        print(f"[INFO] Tłumaczenie EN (model: {translate_model})")
        transcribe(args.audio, translate_model, args.language, args.cpu,
                   task="translate", output_suffix=".en", prompt=args.prompt)
    else:
        transcribe(args.audio, args.model, args.language, args.cpu, prompt=args.prompt)


if __name__ == "__main__":
    main()
