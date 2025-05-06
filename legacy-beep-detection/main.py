import os
import numpy as np
from scipy.io import wavfile
from scipy.signal import fftconvolve, find_peaks
import os


# --- 1. Load Audio Files ---


# fileName = "2019"


def beepSplitter(fileName):
    podcast_sr, podcast_data = wavfile.read("wav/" + fileName + ".wav")
    beep_sr, beep_data = wavfile.read("beep.wav")

    if podcast_sr != beep_sr:
        raise ValueError("Sampling rates of podcast and beep file do not match!")

    if podcast_data.ndim > 1:
        podcast_data = podcast_data.mean(axis=1)
    if beep_data.ndim > 1:
        beep_data = beep_data.mean(axis=1)

    podcast_data = podcast_data.astype(np.float32)
    beep_data = beep_data.astype(np.float32)

    podcast_data /= np.max(np.abs(podcast_data))
    beep_data /= np.max(np.abs(beep_data))

    # --- 2. Compute Cross-Correlation to Detect Beeps ---

    beep_reversed = beep_data[::-1]
    correlation = fftconvolve(podcast_data, beep_reversed, mode="valid")
    threshold = 0.5 * np.max(correlation)
    peaks, _ = find_peaks(correlation, height=threshold, distance=len(beep_data))

    print("Detected beep peaks at sample indices:", peaks)
    beep_times = peaks / podcast_sr
    print("Detected beep times (seconds):", beep_times)

    # --- 3. Segment the Podcast Based on Detected Beep Locations ---

    segments = []
    start_index = 0
    silence_thresh = 0.01  # adjust threshold for “silence”

    for peak in peaks:
        segment = podcast_data[start_index:peak]
        # Only keep the segment if it has sufficient audio (i.e. not silence)
        if np.max(np.abs(segment)) > silence_thresh:
            segments.append(segment)
        else:
            print(f"Skipping silent segment from {start_index} to {peak}")
        start_index = peak

    # Add final segment if non-silent.
    final_segment = podcast_data[start_index:]
    if np.max(np.abs(final_segment)) > silence_thresh:
        segments.append(final_segment)
    else:
        print(f"Skipping final silent segment starting at {start_index}")

    # convert segments into seconds and add them to seconds_segments list
    seconds_segments = []
    for i, segment in enumerate(segments):
        seconds_segments.append(len(segment) / podcast_sr)

    # turn labels into a dictionary with the beep time as the key

    labels = {
        1: "intro",
        2: "go to section a",
        4: "A1234",
        6: "A1",
        8: "A2",
        10: "A3",
        12: "A1234",
        15: "go to section b",
        17: "B1234",
        19: "B1",
        21: "B2",
        23: "B3",
        25: "B4",
        27: "B1234",
        30: "go to section c",
        32: "C123",
        34: "C1",
        36: "C2",
        38: "C3",
        40: "C123",
        43: "go to section d",
        45: "D1234",
        47: "D1",
        49: "D2",
        51: "D3",
        53: "D4",
        55: "D1234",
        58: "go to section E",
        60: "E1",
        62: "E1 (repeated)",
        64: "E2",
        66: "E2 (repeated)",
        68: "E3",
        70: "E3 (repeated)",
        74: "end",
    }

    # create a dictionary with the label values and the corresponding time in seconds
    # labels_seconds = {labels[k]: beep_times[k - 1] for k in labels}
    labels_seconds = {}
    for k in labels:
        idx = k - 1
        if idx < len(beep_times):
            # labels_seconds[labels[k]] = beep_times[idx] # seconds
            labels_seconds[labels[k]] = (
                str(int(beep_times[idx] // 60)) + ":" + str(int(beep_times[idx] % 60))
            )  # minutes and seconds
        else:
            print(
                f"Skipping label '{labels[k]}' because beep index {idx} is out of bounds."
            )

    # save the dictionary to a json file
    import json

    with open("timestamps/" + fileName + ".json", "w") as f:
        json.dump(labels_seconds, f)

    # # # --- 4. Save the Segments as Separate WAV Files in a Folder ---

    # output_folder = fileName + "segments"
    # os.makedirs(output_folder, exist_ok=True)

    # for i, segment in enumerate(segments):
    #     if np.max(np.abs(segment)) > 0:
    #         segment_norm = segment / np.max(np.abs(segment))
    #     else:
    #         segment_norm = segment
    #     segment_int16 = np.int16(segment_norm * 32767)

    #     output_filename = os.path.join(output_folder, f"segment_{i+1}.wav")
    #     wavfile.write(output_filename, podcast_sr, segment_int16)
    #     print(f"Saved {output_filename}")


# beepSplitter("2019")
# beepSplitter("2006")

# --- 5. Run the Beep Splitter on the Audio File ---

# beepSplitter("ga_2024")

os.makedirs("timestamps", exist_ok=True)
wav_folder = "wav"
for file in os.listdir(wav_folder):
    if file.lower().endswith(".wav"):
        base_name = os.path.splitext(file)[0]
        file_path = os.path.join(wav_folder, base_name)
        beepSplitter(base_name)
