# This is a single-file transcription and section analysis script using faster-whisper. dont ask why it has no functions, when i tried that everything self combusted every single god damn time.

import os
import json
import torch
from datetime import datetime
from faster_whisper import WhisperModel
from pathlib import Path
from config import LANGUAGE_CONFIGS

# Minimal helper for timestamp formatting (MM:SS)
format_timestamp = lambda s: f"{int(s // 60):02d}:{int(s % 60):02d}"

# Check for CUDA availability and print device info
print("CUDA available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
    torch.cuda.empty_cache()

# Specify your audio file here (example: audio/2024.mp3)
# audio_file = "audio/2024.mp3"
audio_file = "german2024.mp3"
if not os.path.exists(audio_file):
    print(f"Error: File '{audio_file}' not found!")
    exit(1)

print(f"\nProcessing file: {audio_file}")

# Load the Whisper model (using GPU if available, otherwise it will fail)
print("Loading Whisper model...")
model = WhisperModel("base", device="cuda", compute_type="float16")


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
            # Add more as needed
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
        print(f"\nTimestamps saved to: {output_file}")

    def save_transcript(self, filename: str, segments: list):
        """Save transcript with consistent naming"""
        output_file = self.transcripts_dir / f"{Path(filename).stem}.txt"

        with open(output_file, "w", encoding="utf-8") as f:
            for seg in segments:
                f.write(
                    f"[{format_timestamp(seg['start'])} - {format_timestamp(seg['end'])}]\n"
                )
                f.write(f"{seg['text']}\n\n")

        print(f"Transcript saved to: {output_file}")


def main():
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

    # Load model with optimized settings
    model = WhisperModel(
        "base",
        device="cuda" if torch.cuda.is_available() else "cpu",
        compute_type="float16",
        cpu_threads=2,
        num_workers=1,
    )

    processor = AudioProcessor(language=language, year=Path(audio_files[0]).stem)

    # Process each file
    for audio_file in audio_files:
        try:
            print(f"\nProcessing {audio_file.name}")
            processor.process_file(audio_file.name, model)
            print(f"Successfully processed {audio_file.name}")
        except Exception as e:
            print(f"Error processing {audio_file.name}: {str(e)}")
            continue

    # Cleanup
    del model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


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

# # Language-specific section markers and number formats
# SECTION_PATTERNS = {
#     "fr": {
#         "marker": "section",
#         "numbers": {
#             "a": ["a"],
#             "b": ["b"],
#             "c": ["c"],
#             "d": ["d"],
#             "e": ["e"],
#         },
#     },
#     "de": {
#         "marker": "fragen zu teil",
#         "numbers": {
#             "1": ["eins", "1"],
#             "2": ["zwei", "2"],
#             "3": ["drei", "3"],
#             "4": ["vier", "4"],
#             "5": ["fünf", "5"],
#         },
#     },
#     # Add more languages as needed
#     # "es": {"marker": "sección", "numbers": {...}},
# }


# language = "de"  #

# # Transcribe the audio file
# print("Starting transcription...")
# segments_gen, info = model.transcribe(
#     audio_file,
#     beam_size=5,
#     language=language,
#     task="transcribe",
#     vad_filter=True,
#     vad_parameters=dict(
#         min_silence_duration_ms=300,
#         speech_pad_ms=200,
#     ),
#     word_timestamps=True,
# )
# segments = list(segments_gen)
# print(f"Transcription complete! Found {len(segments)} segments.")

# # Process segments: extract timestamps and text, and build full transcription
# full_text_parts = []
# segments_list = []
# for i, seg in enumerate(segments):
#     # Minimal progress indicator (overwrite previous line)
#     print(f"Processing segment {i+1}/{len(segments)}", end="\r")
#     text = seg.text.strip()
#     segments_list.append({"start": seg.start, "end": seg.end, "text": text})
#     full_text_parts.append(text)
# print("\nFinished processing segments.")
# full_text = " ".join(full_text_parts)

# # Analyze segments for section markers
# section_times = {}
# section_contexts = {}
# pattern = SECTION_PATTERNS.get(language)
# if not pattern:
#     print(f"Warning: No section patterns defined for language '{language}'")
#     pattern = SECTION_PATTERNS["fr"]

# print(f"\nAnalyzing segments for section markers...")
# for i, seg in enumerate(segments_list):
#     lower_text = seg["text"].lower()
#     if pattern["marker"] in lower_text:
#         # Debug output
#         print(f"\nFound potential marker in segment {i+1}:")
#         print(
#             f"Time: [{format_timestamp(seg['start'])} - {format_timestamp(seg['end'])}]"
#         )
#         print(f"Text: {seg['text']}")

#         # Check for exact phrase matches
#         for section_key, variants in pattern["numbers"].items():
#             found_match = False
#             for variant in variants:
#                 exact_marker = f"{pattern['marker']} {variant}"
#                 cleaned_text = (
#                     lower_text.replace(".", " ")
#                     .replace(",", " ")
#                     .replace("!", " ")
#                     .replace("?", " ")
#                 )
#                 if (
#                     f" {exact_marker} " in f" {cleaned_text} "
#                     or cleaned_text.startswith(exact_marker + " ")
#                     or cleaned_text.endswith(" " + exact_marker)
#                 ):
#                     if section_key not in section_times:  # Only take first occurrence
#                         # Get timestamp and context
#                         section_times[section_key] = seg["start"]

#                         # Get surrounding context with timestamps
#                         context_parts = []
#                         if i > 0:
#                             prev_seg = segments_list[i - 1]
#                             context_parts.append(
#                                 f"Previous [{format_timestamp(prev_seg['start'])}]: {prev_seg['text']}"
#                             )
#                         context_parts.append(
#                             f"Current [{format_timestamp(seg['start'])}]: {seg['text']}"
#                         )
#                         if i < len(segments_list) - 1:
#                             next_seg = segments_list[i + 1]
#                             context_parts.append(
#                                 f"Next [{format_timestamp(next_seg['start'])}]: {next_seg['text']}"
#                             )

#                         section_contexts[section_key] = "\n".join(context_parts)
#                         print(
#                             f"-> Matched Section {section_key} at {format_timestamp(seg['start'])}"
#                         )
#                         found_match = True
#                         break
#             if found_match:
#                 break

# if not section_times:
#     print("No section markers found! Here are a few segments for reference:")
#     for i in range(min(5, len(segments_list))):
#         print(f"Segment {i+1}: {segments_list[i]['text']}")

# # Print section timestamps with context
# print("\n=== Section Start Times with Context ===")
# for section, t in sorted(section_times.items()):
#     print(f"\nSection {section}: {format_timestamp(t)}")
#     print(f'Context: "{section_contexts[section]}"')

# # Print a sample of segments (first 3 and last 3 if many)
# print("\n=== Sample Segments ===")
# for i in range(min(3, len(segments_list))):
#     seg = segments_list[i]
#     print(f"\nSegment {i+1}")
#     print(f"Time: {format_timestamp(seg['start'])} - {format_timestamp(seg['end'])}")
#     print(f"Text: {seg['text']}")
#     print("-" * 80)
# if len(segments_list) > 6:
#     print("\n... (skipping middle segments) ...")
#     for i in range(len(segments_list) - 3, len(segments_list)):
#         seg = segments_list[i]
#         print(f"\nSegment {i+1}")
#         print(
#             f"Time: {format_timestamp(seg['start'])} - {format_timestamp(seg['end'])}"
#         )
#         print(f"Text: {seg['text']}")
#         print("-" * 80)

# # Save section timestamps to JSON
# os.makedirs("whisper_timestamps", exist_ok=True)
# base_name = os.path.splitext(os.path.basename(audio_file))[0]
# timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
# output_file = f"whisper_timestamps/{base_name}_{timestamp_str}.json"
# formatted_times = {
#     sec: {"seconds": t, "formatted": format_timestamp(t)}
#     for sec, t in section_times.items()
# }
# with open(output_file, "w", encoding="utf-8") as f:
#     json.dump(formatted_times, f, indent=4)
# print(f"\nTimestamps saved to: {output_file}")

# # Save full transcript to text file
# base_name = os.path.splitext(os.path.basename(audio_file))[0]
# transcript_file = f"{base_name}.txt"
# print(f"\nSaving full transcript to: {transcript_file}")
# with open(transcript_file, "w", encoding="utf-8") as f:
#     # Write timestamps and text for each segment
#     for seg in segments_list:
#         f.write(
#             f"[{format_timestamp(seg['start'])} - {format_timestamp(seg['end'])}]\n"
#         )
#         f.write(f"{seg['text']}\n\n")

# # Print full transcription summary
# print("\n=== Full Transcription ===")
# print(full_text[:500] + "...")
# print(f"\nTotal transcription length: {len(full_text)} characters")

# print("\nProgram complete.")
# # Example reference: Check out faster-whisper documentation at https://github.com/guillaumekln/faster-whisper
# # Note: Inlining all logic like this is less maintainable. Use functions in production!
