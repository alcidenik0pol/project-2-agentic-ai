"""Direct REST call to Vertex AI to bypass SDK and test raw API access."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from google.oauth2 import service_account
import google.auth.transport.requests

# Load credentials
key_path = r'F:\_Dev\_Columbia\Agentic AI\project 2\docs\credentials\agenticaicolumbia-72b6c0b1b975.json'
creds = service_account.Credentials.from_service_account_file(
    key_path,
    scopes=['https://www.googleapis.com/auth/cloud-platform'],
)
creds.refresh(google.auth.transport.requests.Request())
token = creds.token

print(f"Authenticated as: {creds.service_account_email}")
print(f"Token (first 20): {token[:20]}...")
print()

# Try direct REST call to Vertex AI
project = "agenticaicolumbia"
region = "us-central1"
model = "gemini-2.5-flash"

url = f"https://{region}-aiplatform.googleapis.com/v1/projects/{project}/locations/{region}/publishers/google/models/{model}:generateContent"

payload = {
    "contents": [
        {
            "role": "user",
            "parts": [{"text": 'Return ONLY this JSON: {"theme": "test", "is_complaint": false, "intensity": "low"}'}]
        }
    ],
    "generationConfig": {
        "temperature": 0.1,
        "maxOutputTokens": 100,
    }
}

print(f"Calling: {url}")
print()

resp = requests.post(
    url,
    headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    },
    json=payload,
)

print(f"Status: {resp.status_code}")
print(f"Response:")
print(json.dumps(resp.json(), indent=2)[:2000])
