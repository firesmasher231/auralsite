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
    "ga": "Irish",
}

# Initialize output structure
output = {}

# Process each language
for lang_code, lang_name in language_codes.items():
    output[lang_code] = {
        "name": lang_name,
        "enabled": lang_code
        in [
            "fr",
            "de",
            "zh",
            "ga",
        ],  # Only French, German, Mandarin Chinese, and Irish enabled
        "examLinks": {},
    }

    # Look for audio files in each year
    for year in range(2004, 2025):
        year_str = str(year)
        exam_audio_link = None  # from the language branch
        marking_scheme_link = None  # marking scheme link to be retrieved
        aural_paper_link = None  # aural paper link to be retrieved

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

        # Now, try to get the marking scheme from the current language branch.
        marking_source = data["lc"].get(lang_name, {})
        if year_str in marking_source:
            marking_schemes = {}
            aural_papers = {}
            for item in marking_source[year_str]:
                detail = item.get("details", "").lower()
                if item.get("type", "").lower() == "marking scheme":
                    marking_scheme_file_url = (
                        item["url"]
                        if item["url"].startswith("http")
                        else f"{MARKING_BASE_URL}/{year}/{item['url']}"
                    )
                    # Only include marking schemes with EV.pdf in the URL.
                    if not marking_scheme_file_url.endswith("EV.pdf"):
                        if lang_name == "Irish":
                            if "higher" in detail:
                                marking_schemes["higherLevel"] = marking_scheme_file_url
                            elif "ordinary" in detail:
                                marking_schemes["ordinaryLevel"] = (
                                    marking_scheme_file_url
                                )
                            elif "common" in detail:
                                marking_schemes["commonLevel"] = marking_scheme_file_url
                        continue
                    if "higher" in detail:
                        marking_schemes["higherLevel"] = marking_scheme_file_url
                    elif "ordinary" in detail:
                        marking_schemes["ordinaryLevel"] = marking_scheme_file_url
                    elif "common" in detail:
                        marking_schemes["commonLevel"] = marking_scheme_file_url

                elif "aural paper" in detail:
                    aural_paper_file_url = (
                        item["url"]
                        if item["url"].startswith("http")
                        else f"{BASE_URL}/{year}/{item['url']}"
                    )
                    if "iv" in detail:
                        if lang_name == "Irish":
                            if "higher" in detail:
                                print(
                                    f"Added {lang_name} {year} {detail} aural paper to higher level"
                                )
                                aural_papers["higherLevel"] = aural_paper_file_url
                            elif "ordinary" in detail:
                                print(
                                    f"Added {lang_name} {year} {detail} aural paper to ordinary level"
                                )
                                aural_papers["ordinaryLevel"] = aural_paper_file_url
                            else:
                                print(
                                    f"Skipping {lang_name} {year} {detail} aural paper because it doesn't contain iv"
                                )
                                continue
                        elif "higher" in detail:
                            aural_papers["higherLevel"] = aural_paper_file_url
                        elif "ordinary" in detail:
                            aural_papers["ordinaryLevel"] = aural_paper_file_url

            if marking_schemes:
                marking_scheme_link = marking_schemes
            if aural_papers:
                aural_paper_link = aural_papers

        # Only add the year if we have at least one link
        if exam_audio_link or marking_scheme_link:
            output[lang_code]["examLinks"][year_str] = {
                "examAudio": exam_audio_link,
                "markingScheme": marking_scheme_link,
                "auralPaper": aural_paper_link,
            }

# Save the output
with open("languages.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=4)

print("Done! Check languages.json for the extracted links.")
