import json
import re

# Base URL to be prepended if the file name is a relative link for exam audio.
BASE_URL = "https://www.examinations.ie/archive/exampapers"
# Base URL to be prepended if the file name is a relative link for marking schemes.
MARKING_BASE_URL = "https://www.examinations.ie/archive/markingschemes"


# Fix any invalid escape sequences in the JSON string.
def fix_escapes(s):
    return re.sub(r'\\(?!["\\/bfnrt])', r"\\\\", s)


# Load the JSON data from file (adjust the path, if needed)
with open("gettingaudio/data.json", "r", encoding="utf-8") as f:
    content = f.read()
    fixed_content = fix_escapes(content)
    data = json.loads(fixed_content)

# Initialize language codes
language_codes = {
    "fr": "French",
    "de": "German",
    "es": "Spanish",
    "it": "Italian",
    "zh": "Mandarin Chinese",
}

# Initialize output structure
output = {}

# Process each language
for lang_code, lang_name in language_codes.items():
    output[lang_code] = {
        "name": lang_name,
        "enabled": lang_code
        in ["fr", "de", "zh"],  # Only French, German, and Mandarin Chinese enabled
        "examLinks": {},
    }

    # Look for audio files in each year
    for year in range(2004, 2025):
        year_str = str(year)
        exam_audio_link = None  # from the language branch
        marking_scheme_link = None  # marking scheme link to be retrieved

        # Try to get the exam audio file from the target language data if available
        if year_str in data["lc"].get(lang_name, {}):
            for item in data["lc"][lang_name][year_str]:
                if item["url"].lower().endswith(".mp3"):
                    exam_audio_link = (
                        item["url"]
                        if item["url"].startswith("http")
                        else f"{BASE_URL}/{year}/{item['url']}"
                    )
                    break

        # Now, try to get the marking scheme.
        # Use marking schemes from the English branch if it exists,
        # otherwise use the current language branch.
        marking_source = data["lc"].get("English") or data["lc"].get(lang_name, {})
        if year_str in marking_source:
            marking_schemes = {}
            for item in marking_source[year_str]:
                if item.get("type", "").lower() == "marking scheme":
                    detail = item.get("details", "").lower()
                    file_url = (
                        item["url"]
                        if item["url"].startswith("http")
                        else f"{MARKING_BASE_URL}/{year}/{item['url']}"
                    )
                    if "higher" in detail:
                        marking_schemes["higherLevel"] = file_url
                    elif "ordinary" in detail:
                        marking_schemes["ordinaryLevel"] = file_url
                    elif "common" in detail:
                        marking_schemes["commonLevel"] = file_url
            if marking_schemes:
                marking_scheme_link = marking_schemes

        # Only add the year if we have at least one link
        if exam_audio_link or marking_scheme_link:
            output[lang_code]["examLinks"][year_str] = {
                "examAudio": exam_audio_link,
                "markingScheme": marking_scheme_link,
            }

# Save the output
with open("languages.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=4)

print("Done! Check languages.json for the extracted links.")
