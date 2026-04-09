"""Check if Vertex AI API is enabled on the project."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from google.oauth2 import service_account
import google.auth.transport.requests

creds = service_account.Credentials.from_service_account_file(
    r'F:\_Dev\_Columbia\Agentic AI\project 2\docs\credentials\agenticaicolumbia-72b6c0b1b975.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform'],
)
creds.refresh(google.auth.transport.requests.Request())
token = creds.token

resp = requests.get(
    'https://serviceusage.googleapis.com/v1/projects/agenticaicolumbia/services?filter=state:ENABLED',
    headers={'Authorization': f'Bearer {token}'},
)
data = resp.json()

aiplatform = [s for s in data.get('services', []) if 'aiplatform' in s.get('name', '')]
print('Vertex AI API enabled:', bool(aiplatform))
for s in aiplatform:
    print(f"  {s['name']} → {s['state']}")

if not aiplatform:
    print()
    print('ENABLE THESE APIs in Google Cloud Console:')
    print('  https://console.cloud.google.com/apis/library/aiplatform.googleapis.com?project=agenticaicolumbia')
