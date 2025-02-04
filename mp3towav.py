import os
import subprocess

# Define the paths
mp3_folder = 'audio'
wav_folder = 'wav'

# Create the wav folder if it doesn't exist
if not os.path.exists(wav_folder):
    os.makedirs(wav_folder)

# Loop through all files in the mp3 folder
for filename in os.listdir(mp3_folder):
    if filename.endswith('.mp3'):
        # Define the full path for the input and output files
        mp3_path = os.path.join(mp3_folder, filename)
        wav_filename = os.path.splitext(filename)[0] + '.wav'
        wav_path = os.path.join(wav_folder, wav_filename)
        
        # Use ffmpeg to convert the file
        subprocess.run(['ffmpeg', '-i', mp3_path, '-ar', '44100', wav_path])

print("Conversion complete.")