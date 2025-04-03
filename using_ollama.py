import ollama
import json

# Read the transcript file
transcript = open("2019.txt", "r", encoding="utf-8").read()

# Send chat to the model
response = ollama.chat(
    model="deepseek-r1:7b",
    messages=[
        {
            "role": "user",
            "content": (
                transcript + "\n\n"
                "Extract the timestamps of when each *unique* section starts from the transcript. "
                "Ignore repeated replays. The timestamps are in the format of '00:00' for each section start. "
                "Convert each into total seconds. Your response should be in this exact JSON format:\n"
                '{"1": {"seconds": 63}, "2": {"seconds": 323}, "3": {"seconds": 745}, "4": {"seconds": 1159}, '
                '"5": {"seconds": 1481}, "6": {"seconds": 1856}, "7": {"seconds": 2081}}'
            )
        }
    ],
    stream=False,
)

# Print formatted JSON result
try:
    print(json.dumps(json.loads(response["message"]["content"]), indent=2))
except json.JSONDecodeError:
    print("Raw output:\n", response["message"]["content"])
