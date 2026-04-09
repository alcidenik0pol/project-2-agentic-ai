"""Debug script to test what Gemini returns for expansion prompts."""

from app.analyst.providers.gcloud import GCloudProvider
import json

provider = GCloudProvider()

prompt = """You are analyzing Reddit complaints to improve semantic clustering.

Your task: Expand each short theme label into a full, descriptive sentence that captures the essence of the complaint.

Output format: Return ONLY a JSON object mapping each theme to its expanded description.

Real data to process:
{"low salary": ["Pay is too low", "Cant afford rent"], "bad management": ["Boss is toxic", "Micromanaging"]}

Return ONLY the JSON object, no additional text."""

raw = provider.generate_text(prompt, temperature=0.3, max_tokens=256)
print("RAW RESPONSE:")
print(repr(raw))
print()
print("TYPE:", type(raw))

if raw:
    try:
        parsed = json.loads(raw.strip())
        print("PARSED OK:", parsed)
    except json.JSONDecodeError as e:
        print("JSON PARSE FAILED:", e)
        # Try to extract JSON from markdown
        import re
        match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', raw)
        if match:
            print("Found in markdown block:", match.group(1))
        match2 = re.search(r'\{[\s\S]*\}', raw)
        if match2:
            print("Found bare JSON:", match2.group(0))
