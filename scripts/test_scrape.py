import requests
from bs4 import BeautifulSoup

company = "Microsoft"
url = f"https://careers.{company.lower()}.com/"
try:
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"}
    response = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {response.status_code}")
    soup = BeautifulSoup(response.text, 'html.parser')
    text = soup.get_text(separator=' ', strip=True)
    print("Content preview:")
    print(text[:500])
except Exception as e:
    print(f"Error: {e}")
