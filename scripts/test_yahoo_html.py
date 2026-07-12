import urllib.parse
from playwright.sync_api import sync_playwright

def test():
    query = urllib.parse.quote('"Microsoft" software engineer careers')
    url = f"https://search.yahoo.com/search?p={query}"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
        page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        page.goto(url)
        
        try:
            if page.locator("button.agree, button[name='agree']").count() > 0:
                page.locator("button.agree, button[name='agree']").first.click()
        except:
            pass
            
        page.wait_for_timeout(2000)
        
        results = page.locator("div.algo").all()
        for r in results[:3]:
            a_loc = r.locator("a").first
            title = ""
            href = ""
            if a_loc.count() > 0:
                href = a_loc.get_attribute("href")
                h3 = r.locator("h3").first
                title = h3.text_content() if h3.count() > 0 else a_loc.text_content()
            body = r.text_content()
            print(f"TITLE: {title}")
            print(f"HREF: {href}")
            print(f"BODY: {body[:100]}...\n")
        browser.close()

if __name__ == "__main__":
    test()
