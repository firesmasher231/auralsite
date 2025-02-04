import os
import json
import torch
from datetime import datetime
from faster_whisper import WhisperModel
from pathlib import Path
from config import LANGUAGE_CONFIGS
import multiprocessing as mp
from tqdm import tqdm
import psutil
import time

# Minimal helper for timestamp formatting (MM:SS)
format_timestamp = lambda s: f"{int(s // 60):02d}:{int(s % 60):02d}"


def process_single_file(args):
    """Process a single audio file - used by the multiprocessing pool"""
    audio_file, language, model_path, gpu_id = args

    try:
        # Set specific GPU for this process
        torch.cuda.set_device(gpu_id)
        print(f"\nProcess using GPU {gpu_id} for {audio_file.name}")

        # Load model with optimized settings
        model = WhisperModel(
            "base",
            device=f"cuda:{gpu_id}",
            compute_type="float16",
            cpu_threads=2,
            num_workers=1,
        )

        processor = AudioProcessor(language=language, year=Path(audio_file).stem)
        result = processor.process_file(audio_file.name, model)

        # Cleanup
        del model
        torch.cuda.empty_cache()

        return f"Successfully processed {audio_file.name}"
    except Exception as e:
        torch.cuda.empty_cache()
        return f"Error processing {audio_file.name}: {str(e)}"


class AudioProcessor:
    def __init__(self, language: str, year: str):
        self.language = language
        self.year = year
        self.config = LANGUAGE_CONFIGS.get(language)
        if not self.config:
            raise ValueError(f"Unsupported language: {language}")

        # Setup paths
        self.base_dir = Path(__file__).parent
        self.audio_dir = Path("audio") / language
        self.timestamps_dir = self.base_dir / "timestamps" / language
        self.transcripts_dir = self.base_dir / "transcripts" / language

        # Create directories if they don't exist
        self.timestamps_dir.mkdir(parents=True, exist_ok=True)
        self.transcripts_dir.mkdir(parents=True, exist_ok=True)

    def get_language_name(self, lang_code: str) -> str:
        """Convert language code to full name as used by getter.py"""
        language_names = {
            "de": "german",
            "fr": "french",
            "es": "spanish",
            "it": "italian",
            "ie": "irish",
        }
        return language_names.get(lang_code, lang_code)

    def get_section_marker(self, text: str, timestamp: float) -> tuple[str, float]:
        """
        Find section markers based on language config.
        Returns (section_key, timestamp) or (None, None)
        """
        markers = self.config["section_marker"]
        # Convert to list if it's a single string
        if isinstance(markers, str):
            markers = [markers]

        cleaned_text = (
            text.lower()
            .replace(".", " ")
            .replace(",", " ")
            .replace("!", " ")
            .replace("?", " ")
        )

        for section_key, variants in self.config["sections"].items():
            for variant in variants:
                # Try each marker
                for marker in markers:
                    exact_marker = f"{marker} {variant}"
                    if (
                        f" {exact_marker} " in f" {cleaned_text} "
                        or cleaned_text.startswith(exact_marker + " ")
                        or cleaned_text.endswith(" " + exact_marker)
                    ):
                        return section_key, timestamp
        return None, None

    def process_file(self, filename: str, model: WhisperModel):
        """Process a single audio file using provided model instance"""
        audio_path = self.audio_dir / filename
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Transcribe using whisper with optimized settings
        segments_gen, info = model.transcribe(
            str(audio_path),
            beam_size=5,
            language=self.language,
            task="transcribe",
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=300,
                speech_pad_ms=200,
            ),
            word_timestamps=True,
            best_of=2,  # Reduced from default to save VRAM
            patience=1,  # Reduced from default to save VRAM
            compression_ratio_threshold=2.4,
            no_speech_threshold=0.6,
            condition_on_previous_text=True,
        )
        segments = list(segments_gen)

        # Process segments
        section_times = {}
        section_contexts = {}
        segments_list = []
        full_text_parts = []

        for i, seg in enumerate(segments):
            text = seg.text.strip()
            segments_list.append({"start": seg.start, "end": seg.end, "text": text})
            full_text_parts.append(text)

            # Check for section marker
            section_key, timestamp = self.get_section_marker(text, seg.start)
            if section_key and section_key not in section_times:
                section_times[section_key] = timestamp

                # Get context
                context_parts = []
                if i > 0:
                    prev_seg = segments_list[i - 1]
                    context_parts.append(
                        f"Previous [{format_timestamp(prev_seg['start'])}]: {prev_seg['text']}"
                    )
                context_parts.append(f"Current [{format_timestamp(seg.start)}]: {text}")
                if i < len(segments) - 1:
                    next_seg = segments[i + 1]
                    context_parts.append(
                        f"Next [{format_timestamp(next_seg.start)}]: {next_seg.text}"
                    )
                section_contexts[section_key] = "\n".join(context_parts)

        # Save results
        self.save_timestamps(filename, section_times, section_contexts)
        self.save_transcript(filename, segments_list)

        return section_times, section_contexts, segments_list

    def save_timestamps(self, filename: str, times: dict, contexts: dict):
        """Save timestamps with simplified naming and format"""
        # Get year from filename
        year = Path(filename).stem
        output_file = self.timestamps_dir / f"{year}.json"

        # Simplify the timestamps format
        formatted_times = {
            sec: {
                "seconds": t,
            }
            for sec, t in times.items()
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(formatted_times, f, indent=4)

    def save_transcript(self, filename: str, segments: list):
        """Save transcript with consistent naming"""
        output_file = self.transcripts_dir / f"{Path(filename).stem}.txt"

        with open(output_file, "w", encoding="utf-8") as f:
            for seg in segments:
                f.write(
                    f"[{format_timestamp(seg['start'])} - {format_timestamp(seg['end'])}]\n"
                )
                f.write(f"{seg['text']}\n\n")


def main():
    print("CUDA available:", torch.cuda.is_available())
    if torch.cuda.is_available():
        print("GPU:", torch.cuda.get_device_name(0))
        torch.cuda.empty_cache()

    # Process one language at a time
    language = "es"  # Change this to the language you want to process
    audio_dir = Path(f"audio/{language}")
    if not audio_dir.exists():
        print(f"Directory {audio_dir} does not exist")
        return

    audio_files = list(audio_dir.glob("*.mp3"))
    if not audio_files:
        print(f"No MP3 files found in {audio_dir}")
        return

    # Sort files chronologically
    audio_files.sort()
    print(f"\nProcessing {len(audio_files)} {language} files...")

    # Split files into chunks for batch processing
    chunk_size = 5  # Process 5 files at a time
    file_chunks = [
        audio_files[i : i + chunk_size] for i in range(0, len(audio_files), chunk_size)
    ]

    # Process files in chunks with 2 processes
    num_processes = 2
    print(f"\nUsing {num_processes} parallel processes")

    for chunk_idx, chunk in enumerate(file_chunks):
        print(f"\nProcessing chunk {chunk_idx + 1}/{len(file_chunks)}")

        # Prepare arguments for this chunk
        process_args = [
            (f, language, "base", i % num_processes) for i, f in enumerate(chunk)
        ]

        # Process chunk with parallel processes
        with mp.Pool(num_processes) as pool:
            try:
                results = list(
                    tqdm(
                        pool.imap(process_single_file, process_args),
                        total=len(process_args),
                        desc=f"Processing chunk {chunk_idx + 1}",
                    )
                )

                # Print results for this chunk
                for result in results:
                    print(result)

            except Exception as e:
                print(f"Error in processing pool: {str(e)}")
                continue

        # Clear GPU memory between chunks
        torch.cuda.empty_cache()

        # Optional: Add a small delay between chunks
        time.sleep(2)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProcessing interrupted by user")
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
    finally:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
