import openai
import os
import json
from dotenv import load_dotenv
import time

# Load environment variables from .env file
load_dotenv()

# Use environment variable for API key
openai.api_key = os.getenv("OPENAI_API_KEY")


def get_section_changes(transcript_text, lang_code):
    system_prompt = "You are an expert transcript analyzer. Your job is to detect when new sections start in a language listening comprehension exam and output their timestamps in the required format."

    if lang_code == "ga":
        user_prompt = f"""
You are given a transcript of a listening comprehension exam in {lang_code} language. The exam contains multiple sections, each introduced with timestamps (e.g., [00:00 - 00:21]) and section labels like "1. [Section Name]", "2. [Section Name]", or section names in their respective languages (e.g., Cuid A for Irish).

Each section is typically **repeated up to 3 times**, but you must **only include the first time** each section appears.

🎯 Your task:
- Detect when each of the **first three sections** begins.
- Each section corresponds to a part of the paper:
    - Section A = 1
    - Section B = 2
    - Section C = 3
- Extract the section number and the **timestamp in seconds** of when it begins.

📌 Notes:
- Ignore any introductions or repeated replays.
- Convert local numbering systems (e.g., "Ceist a haon") to Arabic numerals: 1, 2, 3.
- Only detect and return the **first appearance** of sections 1, 2, and 3.

📦 Return format:
Return a JSON object with this exact structure:
{{
    "1": {{
        "seconds": [timestamp]
    }},
    "2": {{
        "seconds": [timestamp]
    }},
    "3": {{
        "seconds": [timestamp]
    }}
}}

⚠️ Important:
- Section numbers must be strings ("1", "2", "3")
- Do not include any extra fields, labels, or explanations
- Use decimal points in seconds (e.g., 59.1)
- If a section is missing, do not include it in the output

Now, here is the transcript:
{transcript_text}
"""
    else:
        user_prompt = f"""
You are given a transcript of a listening comprehension exam in {lang_code} language. The exam contains multiple sections, each introduced with timestamps (e.g., [00:00 - 00:21]) and section labels like "1. [Section Name]", "2. [Section Name]", or section name in their respective langauges, eg: Cúid A for Irish.

Each section is typically **repeated up to 3 times**, but you must **only include the first time** each section appears.

🎯 Your task:
- Detect when a **new section** starts.
- For sections numbered 1-7, extract the section number and the timestamp in seconds. (not every language has 7 sections)
- Ignore the introduction section.

📌 Notes:
- Ignore repeated replays of the same section.
- Only include sections labeled with numbers (1 through 7).
- Use the timestamp to determine the exact start time in seconds, if unsure, be generous.
- If a language uses different numbering systems, convert to standard Arabic numerals (1, 2, 3).

📦 Return format:
You must return a JSON object with this exact structure:
{{
    "1": {{
        "seconds": 59.1
    }},
    "2": {{
        "seconds": 323.6
    }},
    ... (and so on for sections 3-7)
}}

⚠️ Important: 
- Section numbers must be strings, not integers in the final JSON
- Only include the section number and seconds, no labels or descriptions
- Be precise with the seconds, using decimal points if needed
- If a section is missing or cannot be found, do not include it in the output
Remember, include the start of the question

Now, here is the transcript:
{transcript_text}
"""

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )

    return response.choices[0].message.content


# # Load transcript from file
# with open("2018.txt", "r", encoding="utf-8") as f:
#     transcript_text = f.read()

# # Get cleaned section transitions and print raw response
# response_text = get_section_changes(transcript_text)
# print(response_text)

# # Clean the response text by removing markdown code block formatting
# cleaned_response = response_text
# if cleaned_response.startswith("```json"):
#     cleaned_response = cleaned_response.replace("```json", "", 1)
# if cleaned_response.endswith("```"):
#     cleaned_response = cleaned_response.rsplit("```", 1)[0]
# cleaned_response = cleaned_response.strip()

# # Parse the JSON response and write to file
# try:
#     parsed_json = json.loads(cleaned_response)
#     with open("2018.json", "w", encoding="utf-8") as f:
#         json.dump(parsed_json, f, indent=2)
#     print("Successfully wrote to timestamps/es/2019.json")
# except json.JSONDecodeError as e:
#     print(f"Error parsing JSON response: {e}")
#     print("Raw response:", response_text)


def process_transcript(file_path, lang_code):
    with open(file_path, "r", encoding="utf-8") as f:
        transcript_text = f.read()

    response_text = get_section_changes(transcript_text, lang_code)
    # print(response_text)

    # Clean the response text by removing markdown code block formatting
    cleaned_response = response_text
    if cleaned_response.startswith("```json"):
        cleaned_response = cleaned_response.replace("```json", "", 1)
    if cleaned_response.endswith("```"):
        cleaned_response = cleaned_response.rsplit("```", 1)[0]
    cleaned_response = cleaned_response.strip()

    # Parse the JSON response and write to file
    try:
        parsed_json = json.loads(cleaned_response)
        output_filename = os.path.splitext(os.path.basename(file_path))[0] + ".json"
        with open(
            f"timestamps/{lang_code}/{output_filename}",
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(parsed_json, f, indent=2)
        print(f"Successfully wrote to timestamps/{lang_code}/{output_filename}")
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        print("Raw response:", response_text)


import time

# Example of how to process multiple languages:
# Spanish example
# for file in os.listdir("transcripts/es"):
#     lang_code = "es"
#     process_transcript(f"transcripts/es/{file}", lang_code)
#     time.sleep(20)

# Irish example
# process_transcript("1995.txt", "ga")
# process_transcript("transcripts/ga/2022.txt", "ga")
process_transcript("2024.txt", "zh")
