"""Check all enabled APIs on the project."""
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
    'https://serviceusage.googleapis.com/v1/projects/agenticaicolumbia/services?filter=state:ENABLED&pageSize=200',
    headers={'Authorization': f'Bearer {token}'},
)
data = resp.json()

services = data.get('services', [])
print(f"Total enabled APIs: {len(services)}")
print()

# Show all enabled APIs
for s in sorted(services, key=lambda x: x['name']):
    name = s['name'].replace('projects/agenticaicolumbia/services/', '')
    print(f"  {name}")
