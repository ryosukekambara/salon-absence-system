from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    response = page.goto('https://salonboard.com/login/')
    
    print("Status:", response.status)
    print("\n=== Response Headers ===")
    for key, value in response.headers.items():
        if any(x in key.lower() for x in ['server', 'akamai', 'cf', 'x-', 'via']):
            print(f"{key}: {value}")
    
    browser.close()
