import numpy as np
from scipy.io import wavfile
from scipy.signal import fftconvolve, find_peaks
import json

def parse_transcript(file_path):
    """
    Parses a transcript file to extract labels for each beep group.
    
    The expected format is:
    
        START OF AUDIO CLIP:
        Beep

        - intro to examination info ( hosted by SEC )
        - French ( ordinary and higher )

        Beep

        - Section A ( go to section A )
        
        Beep
        Beep

        - audio for Q1,2 and 3 at once 
        ...
        END OF AUDIO CLIP

    This function ignores the START/END markers, groups consecutive "Beep" lines,
    and then takes the following label lines (which start with a "-") as the annotation
    for that beep group. It returns a list of label strings in order.
    """
    labels = []
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Remove extra whitespace and ignore empty lines or start/end markers.
    cleaned = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.upper() in {"START OF AUDIO CLIP:", "END OF AUDIO CLIP"}:
            continue
        cleaned.append(line)
    
    # We expect a series of lines that are either "Beep" or label lines (starting with "-").
    # We group consecutive "Beep" lines into one beep group and then collect the following label lines.
    in_beep_group = False
    current_label_lines = []
    
    for line in cleaned:
        if line.lower() == "beep":
            # If we hit a beep marker and we already had some label lines collected,
            # that means the label block for the previous beep group is complete.
            if current_label_lines:
                label = " ".join(current_label_lines)
                labels.append(label)
                current_label_lines = []
            in_beep_group = True
        elif line.startswith("-"):
            # If we are in a beep group, then this label belongs to that group.
            if in_beep_group:
                current_label_lines.append(line.lstrip("-").strip())
            else:
                # If not preceded by an explicit beep (should not happen), just add it.
                current_label_lines.append(line.lstrip("-").strip())
        else:
            # Any other line is ignored for now.
            continue
    # If there is any label text left at the end, add it as one label.
    if current_label_lines:
        label = " ".join(current_label_lines)
        labels.append(label)
    
    return labels

def group_beep_times(beep_times, grouping_threshold=0.5):
    """
    Groups beep times if consecutive beeps are closer than grouping_threshold seconds.
    
    Returns a list of representative beep times (one per group). Here we choose the last
    beep in each group as the group’s representative boundary.
    """
    if len(beep_times) == 0:
        return []
    
    groups = []
    current_group = [beep_times[0]]
    for t in beep_times[1:]:
        if t - current_group[-1] < grouping_threshold:
            current_group.append(t)
        else:
            groups.append(current_group[-1])
            current_group = [t]
    groups.append(current_group[-1])
    return groups

def main():
    # === 1. Load Audio Files ===
    podcast_sr, podcast_data = wavfile.read('firstbit.wav')
    beep_sr, beep_data = wavfile.read('beep.wav')
    
    if podcast_sr != beep_sr:
        raise ValueError("Sampling rates do not match!")
    
    # If stereo, convert to mono by averaging channels.
    if podcast_data.ndim > 1:
        podcast_data = podcast_data.mean(axis=1)
    if beep_data.ndim > 1:
        beep_data = beep_data.mean(axis=1)
    
    # Convert to float and normalize to the range [-1, 1]
    podcast_data = podcast_data.astype(np.float32)
    beep_data = beep_data.astype(np.float32)
    podcast_data /= np.max(np.abs(podcast_data))
    beep_data /= np.max(np.abs(beep_data))
    
    # === 2. Detect Beep Times via Cross-Correlation ===
    beep_reversed = beep_data[::-1]
    correlation = fftconvolve(podcast_data, beep_reversed, mode='valid')
    threshold = 0.5 * np.max(correlation)
    
    # Use find_peaks with a minimum distance (to avoid detecting the same beep multiple times)
    peaks, _ = find_peaks(correlation, height=threshold, distance=len(beep_data))
    print("Detected beep peaks (sample indices):", peaks)
    
    # Convert sample indices to seconds.
    detected_beep_times = peaks / podcast_sr
    print("Detected beep times (seconds):", detected_beep_times)
    
    # Group beep times that occur close together (as in the transcript, which may have consecutive beeps)
    grouped_beep_times = group_beep_times(detected_beep_times, grouping_threshold=0.5)
    print("Grouped beep times (seconds):", grouped_beep_times)
    
    # === 3. Parse the Transcript for Auto‑Labels ===
    transcript_labels = parse_transcript("transcript.txt")
    print("Parsed transcript labels:", transcript_labels)
    
    # Compare the number of beep groups and transcript labels.
    num_groups = len(grouped_beep_times)
    num_labels = len(transcript_labels)
    if num_labels != num_groups:
        print(f"Warning: Number of labels from transcript ({num_labels}) does not match number of beep groups ({num_groups}).")
    
    # === 4. Build Segment Metadata with Auto‑Labels ===
    segments = []
    start_time = 0.0
    # We’ll assign a label to each segment that ends at the representative beep time.
    # The segment boundaries are from start of file (or previous beep group) to current beep group.
    n = min(num_groups, num_labels)
    for i in range(n):
        end_time = grouped_beep_times[i]
        label = transcript_labels[i]
        segments.append({
            "start": start_time,
            "end": end_time,
            "duration": end_time - start_time,
            "label": label
        })
        start_time = end_time
    # If there is any remaining audio after the last beep, add a final segment.
    total_duration = len(podcast_data) / podcast_sr
    if start_time < total_duration:
        segments.append({
            "start": start_time,
            "end": total_duration,
            "duration": total_duration - start_time,
            "label": ""  # No label assigned
        })
    
    # Prepare the final metadata dictionary.
    metadata = {
        "sample_rate": podcast_sr,
        "total_duration": total_duration,
        "grouped_beep_times": grouped_beep_times,
        "segments": segments
    }
    
    # === 5. Save the Metadata as JSON ===
    with open("metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4)
    
    print("Metadata saved to metadata.json")

if __name__ == "__main__":
    main()
