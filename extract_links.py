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
    "fr": {"name": "French", "flag": "🇫🇷"},
    "de": {"name": "German", "flag": "🇩🇪"},
    "es": {"name": "Spanish", "flag": "🇪🇸"},
    "ga": {"name": "Irish", "flag": "🇮🇪"},
    "it": {"name": "Italian", "flag": "🇮🇹"},
    "zh": {"name": "Mandarin Chinese", "flag": "🇨🇳"},
    "lt": {"name": "Lithuanian", "flag": "🇱🇹"},
    "pt": {"name": "Portuguese", "flag": "🇵🇹"},
    "ja": {"name": "Japanese", "flag": "🇯🇵"},
    "ru": {"name": "Russian", "flag": "🇷🇺"},
    "pl": {"name": "Polish", "flag": "🇵🇱"},
}

# Initialize output structure
output = {}

# Process each language
for lang_code, lang_data in language_codes.items():
    output[lang_code] = {
        "name": lang_data["name"],
        "flag": lang_data["flag"],
        "enabled": lang_code
        in [
            "fr",
            "de",
            "zh",
            "ga",
            "it",
            "es",
            "lt",
            "pt",
            "ja",
            "ru",
            "pl",
        ],  # All languages enabled
        "timestamps_disabled": lang_code
        in [
            "ga",
            "lt",
            "pt",
            "ja",
            "ru",
            "pl",
        ],  # Irish and new languages have timestamps disabled
        "examLinks": {},
    }

    # Look for audio files in each year
    for year in range(2004, 2025):
        year_str = str(year)
        exam_audio_link = None  # from the language branch
        marking_scheme_link = None  # marking scheme link to be retrieved
        aural_paper_link = None  # aural paper link to be retrieved

        # Try to get the exam audio file from the target language data if available
        if year_str in data["lc"].get(lang_data["name"], {}):
            for item in data["lc"][lang_data["name"]][year_str]:
                if item["url"].lower().endswith(".mp3"):
                    exam_audio_link = (
                        item["url"]
                        if item["url"].startswith("http")
                        else f"{BASE_URL}/{year}/{item['url']}"
                    )
                    break

        # Now, try to get the marking scheme from the current language branch.
        marking_source = data["lc"].get(lang_data["name"], {})
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
                        if lang_data["name"] == "Irish":
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

                    # Get the filename from the URL for pattern matching
                    filename = item["url"].split("/")[-1].upper()

                    # Different handling for Irish vs other languages
                    if lang_data["name"] == "Irish":
                        # For Irish, look for aural papers with specific filename patterns
                        if "ALPA" in filename and "IV" in filename:
                            print(
                                f"Added {lang_data['name']} {year} aural paper to higher level: {filename}"
                            )
                            aural_papers["higherLevel"] = aural_paper_file_url
                        elif "GLPA" in filename and "IV" in filename:
                            print(
                                f"Added {lang_data['name']} {year} aural paper to ordinary level: {filename}"
                            )
                            aural_papers["ordinaryLevel"] = aural_paper_file_url
                    else:
                        # For other languages
                        if "higher" in detail or "ALPA" in filename:
                            aural_papers["higherLevel"] = aural_paper_file_url
                        elif "ordinary" in detail or "GLPA" in filename:
                            aural_papers["ordinaryLevel"] = aural_paper_file_url

                # Special case for Irish: Paper One contains the aural content
                elif lang_data["name"] == "Irish" and "paper one" in detail.lower():
                    paper_one_file_url = (
                        item["url"]
                        if item["url"].startswith("http")
                        else f"{BASE_URL}/{year}/{item['url']}"
                    )

                    # Get the filename from the URL for pattern matching
                    filename = item["url"].split("/")[-1].upper()

                    if "ALP100IV" in filename:
                        print(
                            f"Added {lang_data['name']} {year} Paper One (aural) to higher level: {filename}"
                        )
                        aural_papers["higherLevel"] = paper_one_file_url
                    elif "GLP100IV" in filename:
                        print(
                            f"Added {lang_data['name']} {year} Paper One (aural) to ordinary level: {filename}"
                        )
                        aural_papers["ordinaryLevel"] = paper_one_file_url

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
