import json
import os
import requests
from pathlib import Path
import unicodedata
import re


def sanitize_filename(name):
    """Convert special characters and remove invalid filename characters"""
    # Normalize unicode characters
    name = unicodedata.normalize("NFKD", name)
    # Remove non-ASCII characters
    name = name.encode("ASCII", "ignore").decode()
    # Replace spaces with underscores and convert to lowercase
    name = re.sub(r"[^\w\s-]", "", name).strip().lower()
    name = re.sub(r"[-\s]+", "_", name)
    return name


def download_file(url, output_path):
    """Download a file from URL to the specified path"""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()

        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False


def get_audio_files(selected_language=None):
    # Load the JSON data
    try:
        with open("data.json", "r", encoding="utf-8") as f:
            content = f.read()
            content = content.replace("\\", "\\\\")
            content = content.replace('\\"', '"')
            data = json.loads(content)
    except Exception as e:
        print(f"Error loading JSON file: {e}")
        return

    base_url = "https://www.examinations.ie/archive/exampapers"

    # Create base audio directory
    base_dir = Path("audio_files")
    base_dir.mkdir(exist_ok=True)

    # Language code mapping
    language_codes = {
        "Irish": "ie",
        "German": "de",
        "French": "fr",
        "Spanish": "es",
        "Italian": "it",
    }

    # Filter languages if a specific one is selected
    languages = (
        {selected_language: data["lc"][selected_language]}
        if selected_language
        else data["lc"]
    )

    # Iterate through languages
    for language, years in languages.items():
        # Get language code and create directory
        lang_code = language_codes.get(language.lower(), language.lower()[:2])
        lang_dir = base_dir / lang_code
        lang_dir.mkdir(exist_ok=True)

        # Create language directory with sanitized name
        safe_language = sanitize_filename(language)
        print(f"Processing language: {language} (directory: {safe_language})")
        lang_dir = base_dir / safe_language
        lang_dir.mkdir(exist_ok=True)

        # Iterate through years
        for year, items in years.items():
            # Look for MP3 files in items
            for item in items:
                if item["url"].lower().endswith(".mp3"):
                    # Construct full URL
                    file_url = f"{base_url}/{year}/{item['url']}"

                    # Construct output path
                    output_path = lang_dir / f"{year}.mp3"

                    # Skip if file already exists
                    if output_path.exists():
                        print(f"Skipping {safe_language}/{year}.mp3 - already exists")
                        continue

                    print(f"Downloading {safe_language}/{year}.mp3")
                    success = download_file(file_url, output_path)

                    if success:
                        print(f"Successfully downloaded {safe_language}/{year}.mp3")
                    else:
                        print(f"Failed to download {safe_language}/{year}.mp3")


if __name__ == "__main__":
    get_audio_files("Spanish")  # Only download Spanish files
