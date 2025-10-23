from playwright.sync_api import sync_playwright

def test_playwright():
    print("Playwrightテスト開始...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        print("Googleにアクセス中...")
        page.goto('https://www.google.com')
        print(f"タイトル: {page.title()}")
        page.wait_for_timeout(5000)
        browser.close()
        print("✅ Playwrightテスト成功！")

if __name__ == '__main__':
    test_playwright()
