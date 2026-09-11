#!/usr/bin/env python3
"""
transcribe.py — Automatyczny skrypt transkrypcji audio do SRT
Silnik: faster-whisper + VAD (silero-vad)
GPU: CUDA (RTX 4060)

Użycie:
    py -3.12 transcribe.py "D:\\Biblioteki\\prawy video\\07.09\\plik.mp3"
    py -3.12 transcribe.py "plik.mp3" --model large-v2 --language pl
    py -3.12 transcribe.py "plik.mp3" --cpu   # fallback CPU

Wyjście: plik .srt w tym samym katalogu co plik wejściowy.
"""

import argparse
import sys
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


def transcribe(audio_path: str, model_size: str, language: str, use_cpu: bool):
    from faster_whisper import WhisperModel

    audio_path = Path(audio_path)
    if not audio_path.exists():
        print(f"[ERROR] Plik nie istnieje: {audio_path}")
        sys.exit(1)

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
    print(f"[INFO] Plik wejściowy: {audio_path}")
    print(f"[INFO] Plik wyjściowy: {output_srt}")
    print("[INFO] Ładowanie modelu...")

    model = WhisperModel(model_size, device=device, compute_type=compute_type)

    print("[INFO] Transkrypcja z VAD... (to może chwilę potrwać)")

    segments, info = model.transcribe(
        str(audio_path),
        language=language,
        condition_on_previous_text=False,
        vad_filter=True,
        vad_parameters=dict(
            min_silence_duration_ms=500,
            threshold=0.5,
            speech_pad_ms=200,
        ),
        word_timestamps=True,
        beam_size=5,
    )

    print(f"[INFO] Wykryty język: {info.language} (pewność: {info.language_probability:.1%})")
    print("[INFO] Zapis SRT...")

    srt_blocks = []
    index = 1

    for segment in segments:
        start = format_timestamp(segment.start)
        end = format_timestamp(segment.end)
        text = segment.text.strip()

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

    args = parser.parse_args()

    if "Python314" in sys.executable or "python314" in sys.executable:
        print("[ERROR] Wykryto Python 3.14 \u2014 deadlock z CUDA. Użyj: py -3.12 transcribe.py")
        sys.exit(1)

    transcribe(args.audio, args.model, args.language, args.cpu)


if __name__ == "__main__":
    main()
