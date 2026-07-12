from playwright.sync_api import sync_playwright

def test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
        page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        page.goto("https://html.duckduckgo.com/html/")
        
        search_box = page.locator("input[name='q']").first
        search_box.fill('"Microsoft" software engineer careers')
        search_box.press("Enter")
        
        page.wait_for_timeout(3000)
        
        html = page.content()
        with open("debug.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("HTML saved to debug.html")
        print("Results count:", page.locator("a.result__url").count())
        browser.close()

if __name__ == "__main__":
    test()
