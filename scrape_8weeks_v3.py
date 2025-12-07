#!/usr/bin/env python3
"""
8週間分の予約をスクレイピングしてbookingsテーブルに保存
詳細ページをスキップ、一覧ページから直接保存
"""
import json
import re
import os
import requests
from datetime import datetime, timedelta, timezone

print(f"[STARTUP] scrape_8weeks_v3.py 開始", flush=True)

JST = timezone(timedelta(hours=9))

def login_to_salonboard(page):
    login_id = os.environ.get('SALONBOARD_LOGIN_ID', 'CD18317')
    login_password = os.environ.get('SALONBOARD_LOGIN_PASSWORD', 'Ne8T2Hhi!')
    
    page.goto('https://salonboard.com/login/', timeout=60000)
    page.wait_for_timeout(3000)
    page.fill('input[name="userId"]', login_id)
    page.fill('input[name="password"]', login_password)
    page.click('a:has-text("ログイン")')
    page.wait_for_timeout(5000)
    
    return 'login' not in page.url.lower()

def main():
    print(f"[{datetime.now(JST)}] 8週間予約スクレイピング開始", flush=True)
    
    try:
        from playwright.sync_api import sync_playwright
        print("[OK] playwright インポート成功", flush=True)
    except Exception as e:
        print(f"[ERROR] playwright インポート失敗: {e}", flush=True)
        return
    
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("[ERROR] SUPABASE環境変数がありません", flush=True)
        return
    
    print(f"[OK] SUPABASE_URL: {SUPABASE_URL[:30]}...", flush=True)
    
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json'
    }
    
    today = datetime.now(JST)
    total_saved = 0
    
    try:
        with sync_playwright() as p:
            print("[OK] Playwright起動", flush=True)
            browser = p.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled'])
            print("[OK] ブラウザ起動", flush=True)
            
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                viewport={'width': 1920, 'height': 1080},
                locale='ja-JP',
                timezone_id='Asia/Tokyo'
            )
            
            try:
                with open('session_cookies.json', 'r') as f:
                    cookies = json.load(f)
                context.add_cookies(cookies)
                print(f"[OK] クッキー読み込み: {len(cookies)}個", flush=True)
            except Exception as e:
                print(f"[WARN] クッキー読み込み失敗: {e}", flush=True)
            
            page = context.new_page()
            
            # 8週間分（56日）をループ
            for day_offset in range(56):
                target_date = today + timedelta(days=day_offset)
                date_str = target_date.strftime('%Y%m%d')
                url = f'https://salonboard.com/KLP/reserve/reserveList/searchDate?date={date_str}'
                
                print(f"[{target_date.strftime('%Y-%m-%d')}] アクセス中...", flush=True)
                
                try:
                    page.goto(url, timeout=60000)
                    page.wait_for_timeout(2000)
                except Exception as e:
                    print(f"[{target_date.strftime('%Y-%m-%d')}] アクセスエラー、スキップ: {e}", flush=True)
                    continue
                
                # ログイン確認（初回のみ）
                if day_offset == 0 and ('login' in page.url.lower() or 'エラー' in page.title() or len(page.query_selector_all('table')) == 0):
                    print("[WARN] ログインが必要", flush=True)
                    if not login_to_salonboard(page):
                        print("[ERROR] ログイン失敗", flush=True)
                        browser.close()
                        return
                    
                    new_cookies = context.cookies()
                    with open('session_cookies.json', 'w') as f:
                        json.dump(new_cookies, f, indent=2, ensure_ascii=False)
                    print("[OK] ログイン成功、クッキー保存", flush=True)
                    
                    page.goto(url, timeout=60000)
                    page.wait_for_timeout(2000)
                
                # デバッグ: ページ構造確認
                tables = page.query_selector_all("table")
                print(f"[DEBUG] テーブル数: {len(tables)}", flush=True)
                if tables:
                    print(f"[DEBUG] 最初のテーブルHTML: {tables[0].inner_html()[:500]}", flush=True)
                
                # 一覧ページから直接予約情報を取得
                rows = page.query_selector_all('table tbody tr')
                day_saved = 0
                
                for row in rows:
                    try:
                        cells = row.query_selector_all('td')
                        if len(cells) < 4:
                            continue
                        
                        # 顧客名から予約ID抽出
                        customer_cell = cells[2].text_content().strip()
                        id_match = re.search(r'\(([A-Z]{2}\d+)\)', customer_cell)
                        booking_id = id_match.group(1) if id_match else None
                        
                        if not booking_id:
                            continue
                        
                        # 顧客名（IDを除去）
                        customer_name = re.sub(r'\s*\([A-Z]{2}\d+\)', '', customer_cell).strip()
                        customer_name = re.sub(r'[★☆♪♡⭐️🦁]', '', customer_name).strip()
                        
                        # 時間
                        time_cell = cells[0].text_content().strip() if len(cells) > 0 else ""
                        visit_datetime = f"{target_date.strftime('%Y/%m/%d')} {time_cell}"
                        
                        # スタッフ
                        staff = cells[1].text_content().strip() if len(cells) > 1 else ""
                        
                        # ソース（NET/NHPB等）
                        source = cells[4].text_content().strip() if len(cells) > 4 else ""
                        
                        if customer_name:
                            data = {
                                'booking_id': booking_id,
                                'customer_name': customer_name,
                                'phone': '',  # 一覧ページには電話番号がない
                                'visit_datetime': visit_datetime,
                                'menu': '',
                                'staff': staff,
                                'status': 'confirmed',
                                'booking_source': source
                            }
                            
                            res = requests.post(
                                f'{SUPABASE_URL}/rest/v1/bookings',
                                headers={**headers, 'Prefer': 'resolution=merge-duplicates'},
                                json=data
                            )
                            
                            if res.status_code in [200, 201]:
                                total_saved += 1
                                day_saved += 1
                    except Exception as e:
                        continue
                
                print(f"[{target_date.strftime('%Y-%m-%d')}] {day_saved}件保存", flush=True)
            
            browser.close()
    except Exception as e:
        print(f"[ERROR] 致命的エラー: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return
    
    print(f"\n[完了] {total_saved}件の予約を保存", flush=True)

if __name__ == "__main__":
    main()
