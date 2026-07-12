import urllib.parse
from playwright.sync_api import sync_playwright

def test():
    query = urllib.parse.quote('"Microsoft" software engineer careers')
    url = f"https://search.yahoo.com/search?p={query}"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
        page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        page.goto(url)
        
        # Wait for search results container
        page.wait_for_timeout(3000)
        
        # Extract results
        results = page.locator("div.algo").all()
        for r in results[:5]:
            title_loc = r.locator("h3.title a").first
            title = title_loc.text_content() if title_loc.count() > 0 else ""
            href = title_loc.get_attribute("href") if title_loc.count() > 0 else ""
            body = r.text_content()
            print(f"TITLE: {title}\nHREF: {href}\nBODY: {body[:100]}...\n")
            
        print(f"Total results found: {len(results)}")
        browser.close()

if __name__ == "__main__":
    test()
