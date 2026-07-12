import urllib.request
import json

req = urllib.request.Request(
    'http://localhost:8000/api/jobs/scrape', 
    data=json.dumps({"max_per_company": 1, "job_type": "internship"}).encode(),
    headers={'Content-Type': 'application/json'}
)
try:
    with urllib.request.urlopen(req) as response:
        print(response.read().decode())
except Exception as e:
    print(e)
