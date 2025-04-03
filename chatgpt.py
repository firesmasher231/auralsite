import openai
import os
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Use environment variable for API key
openai.api_key = os.getenv("OPENAI_API_KEY")


def get_section_changes(transcript_text):
    system_prompt = "You are an expert transcript analyzer. Your job is to detect when new sections start in a Spanish Listening Comprehension exam and output their timestamps in the required format."

    user_prompt = f"""
You are given a transcript of a Listening Comprehension exam. The exam contains multiple sections, each introduced with timestamps (e.g., [00:00 - 00:21]) and section labels like "1. Anuncio", "2. Entrevista", etc.

Each section is typically **repeated up to 3 times**, but you must **only include the first time** each section appears.

🎯 Your task:
- Detect when a **new section** starts.
- For sections numbered 1-7, extract the section number and the timestamp in seconds.
- Ignore the introduction section.

📌 Notes:
- Ignore repeated replays of the same section.
- Only include sections labeled with numbers (1 through 7).
- Use the timestamp to determine the exact start time in seconds.

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

Now, here is the transcript:
{transcript_text}
"""

    response = openai.chat.completions.create(
        model="gpt-4o",  # Consider upgrading to gpt-4o for better accuracy
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


def process_transcript(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        transcript_text = f.read()

    response_text = get_section_changes(transcript_text)
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
        with open(
            f"timestamps/es/{file_path.split('/')[-1].split('.')[0]}.json",
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(parsed_json, f, indent=2)
        print(f"Successfully wrote to timestamps/es/{file_path.split('/')[-1]}")
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        print("Raw response:", response_text)


import time

for file in os.listdir("transcripts/es"):
    process_transcript(f"transcripts/es/{file}")
    time.sleep(20)
