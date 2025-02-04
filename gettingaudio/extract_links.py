import json
import re


def fix_escapes(s):
    # Fix any invalid escape sequences in the string
    return re.sub(r'\\(?!["\\/bfnrt])', r"\\\\", s)


# Load the data with escape sequence handling
with open("gettingaudio/data.json", "r", encoding="utf-8") as f:
    content = f.read()
    fixed_content = fix_escapes(content)
    data = json.loads(fixed_content)

# Initialize language codes
language_codes = {"fr": "French", "de": "German", "es": "Spanish", "it": "Italian"}

# Initialize output structure
output = {}

# Process each language
for lang_code, lang_name in language_codes.items():
    output[lang_code] = {
        "name": lang_name,
        "enabled": lang_code in ["fr", "de"],  # Only French and German enabled
        "examLinks": {},
    }

    # Look for audio files in each year
    for year in range(2004, 2025):
        year_str = str(year)
        if year_str in data["lc"].get(lang_name, {}):
            # Find audio file in this year's data
            for item in data["lc"][lang_name][year_str]:
                if item["url"].lower().endswith(".mp3"):
                    output[lang_code]["examLinks"][
                        year_str
                    ] = f"https://www.examinations.ie/archive/exampapers/{year}/{item['url']}"
                    break

# Save the output
with open("languages.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=4)

print("Done! Check languages.json for the extracted links.")
