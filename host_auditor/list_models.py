
import os
import requests

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("No key")
    exit(1)

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
response = requests.get(url)
print(response.status_code)
print(response.text)
