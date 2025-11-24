#!/usr/bin/env python3
import os
import json
from playwright.sync_api import sync_playwright
from datetime import datetime
from dotenv import load_dotenv
import re
load_dotenv()

def scrape_bookings():
    result_file = f"/tmp/scrape_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    try:
        login_id = os.getenv('SALONBOARD_LOGIN_ID')
        password = os.getenv('SALONBOARD_LOGIN_PASSWORD')
        
        if not login_id or not password:
            raise Exception("環境変数が設定されていません")
        
        print(f"[SCRAPE] スクレイピング開始", flush=True)
        
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            page = browser.new_page()
            page.set_default_timeout(60000)
            
            # ログイン
            print(f"[SCRAPE] ログイン中...", flush=True)
            page.goto('https://salonboard.com/login/', wait_until='domcontentloaded')
            page.wait_for_selector('input[name="userId"]', timeout=30000)
            page.fill('input[name="userId"]', login_id)
            page.fill('input[name="password"]', password)
            page.press('input[name="password"]', 'Enter')
            page.wait_for_url('**/KLP/**', timeout=60000)
            print(f"[SCRAPE] ログイン成功", flush=True)
            
            page.wait_for_timeout(3000)
            
            # 本日の予約一覧
            print(f"[SCRAPE] 本日の予約一覧を取得中...", flush=True)
            page.click('a:has-text("本日の予約")')
            page.wait_for_url('**/reserve/reserveList/**', timeout=30000)
            page.wait_for_timeout(3000)
            
            # 予約情報を抽出
            bookings = []
            seen_ids = set()
            rows = page.query_selector_all('table tbody tr')
            print(f"[SCRAPE] {len(rows)}行を検出", flush=True)
            
            for row in rows:
                try:
                    cells = row.query_selector_all('td')
                    if len(cells) < 4:
                        continue
                    
                    datetime_text = cells[0].text_content().strip()
                    status = cells[1].text_content().strip()
                    customer_name = cells[2].text_content().strip()
                    
                    if datetime_text.isdigit():
                        continue
                    if 'キャンセル' in status:
                        continue
                    
                    id_match = re.search(r'\(([A-Z]{2}\d+)\)', customer_name)
                    booking_id = id_match.group(1) if id_match else customer_name
                    
                    if booking_id in seen_ids:
                        continue
                    seen_ids.add(booking_id)
                    
                    staff = cells[3].text_content().strip() if len(cells) > 3 else ""
                    source = cells[4].text_content().strip() if len(cells) > 4 else ""
                    menu = cells[5].text_content().strip() if len(cells) > 5 else ""
                    
                    booking_data = {
                        "来店日時": datetime_text,
                        "ステータス": status,
                        "お客様名": customer_name,
                        "スタッフ": staff,
                        "予約経路": source,
                        "メニュー": menu,
                        "予約ID": booking_id
                    }
                    bookings.append(booking_data)
                    print(f"[SCRAPE] 取得: {customer_name[:30]}", flush=True)
                
                except Exception as e:
                    continue
            
            browser.close()
            
            result = {
                "success": True,
                "bookings": bookings,
                "count": len(bookings),
                "timestamp": datetime.now().isoformat()
            }
            
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print(f"[SCRAPE] 完了: {len(bookings)}件の予約を取得", flush=True)
            print(f"[SCRAPE] 結果ファイル: {result_file}", flush=True)
            
            return result
            
    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(error_result, f, ensure_ascii=False, indent=2)
        
        print(f"[SCRAPE] エラー: {str(e)}", flush=True)
        raise

if __name__ == "__main__":
    scrape_bookings()
