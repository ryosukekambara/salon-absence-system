#!/usr/bin/env python3
"""
8週間分の予約をスクレイピングして8weeks_bookingsテーブルに保存
詳細ページをスキップ、一覧ページから直接保存
"""
import json
import re
import os
import requests
from datetime import datetime, timedelta, timezone

print(f"[STARTUP] scrape_8weeks_v3.py 開始", flush=True)

JST = timezone(timedelta(hours=9))

SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://lsrbeugmqqqklywmvjjs.supabase.co')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')

def get_phone_for_customer(customer_name, reserve_id, session):
    """顧客の電話番号を取得（customersテーブルから検索）"""
    if not SUPABASE_KEY:
        return ''
    headers = {'apikey': SUPABASE_KEY, 'Authorization': f'Bearer {SUPABASE_KEY}'}
    res = requests.get(
        f'{SUPABASE_URL}/rest/v1/customers?name=ilike.*{customer_name}*&select=phone',
        headers=headers
    )
    if res.status_code == 200 and res.json():
        phone = res.json()[0].get('phone', '')
        if phone:
            print(f"[PHONE] {customer_name} → {phone}")
            return phone
    return ''

def login_to_salonboard(page):
    login_id = os.environ.get('SALONBOARD_LOGIN_ID', 'CD18317')
    login_password = os.environ.get('SALONBOARD_LOGIN_PASSWORD', 'Ne8T2Hhi!')
    
    print(f"[LOGIN] ログインページにアクセス中...", flush=True)
    page.goto('https://salonboard.com/login/', timeout=60000)
    page.wait_for_timeout(5000)
    
    print(f"[LOGIN] 現在のURL: {page.url}", flush=True)
    print(f"[LOGIN] ページタイトル: {page.title()}", flush=True)
    
    # ID入力
    try:
        page.fill('input[name="userId"]', login_id)
        print(f"[LOGIN] ID入力成功", flush=True)
    except Exception as e:
        print(f"[LOGIN] ID入力失敗: {e}", flush=True)
        return False
    
    # パスワード入力
    try:
        page.fill('input[name="password"]', login_password)
        print(f"[LOGIN] パスワード入力成功", flush=True)
    except Exception as e:
        print(f"[LOGIN] パスワード入力失敗: {e}", flush=True)
        return False
    
    # ログインボタンクリック（JavaScript実行）
    try:
        print(f"[LOGIN] JavaScriptでdologin()を実行...", flush=True)
        page.evaluate("dologin(new Event('click'))")
        print(f"[LOGIN] dologin()実行成功", flush=True)
    except Exception as e:
        print(f"[LOGIN] dologin()失敗: {e}", flush=True)
        return False
    
    # ページ遷移を待つ
    try:
        page.wait_for_timeout(3000)  # 3秒待機
        print(f"[LOGIN] 3秒後のURL: {page.url}", flush=True)
        print(f"[LOGIN] 3秒後のタイトル: {page.title()}", flush=True)
        page.wait_for_url("**/KLP/**", timeout=27000)
        print(f"[LOGIN] ページ遷移成功", flush=True)
    except Exception as e:
        print(f"[LOGIN] ページ遷移タイムアウト: {e}", flush=True)
        # エラーメッセージを確認
        error_msg = page.query_selector('.error, .errorMessage, .mod_error')
        if error_msg:
            print(f"[LOGIN] エラーメッセージ: {error_msg.inner_text()}", flush=True)
        print(f"[LOGIN] 現在のURL: {page.url}", flush=True)
        return False
    
    print(f"[LOGIN] ログイン後URL: {page.url}", flush=True)
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
        'Content-Type': 'application/json',
        'Prefer': 'resolution=merge-duplicates'
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
                
                # 予約一覧テーブルを特定（来店日時ヘッダーを持つテーブル）
                reservation_table = None
                tables = page.query_selector_all("table")
                for table in tables:
                    header = table.query_selector("th#comingDate")
                    if header:
                        reservation_table = table
                        break
                
                if not reservation_table:
                    print(f"[{target_date.strftime('%Y-%m-%d')}] 予約一覧テーブルなし、スキップ", flush=True)
                    continue
                
                # 予約一覧テーブルからデータ取得
                rows = reservation_table.query_selector_all('tbody tr')
                print(f"[DEBUG] 予約行数: {len(rows)}", flush=True)
                day_saved = 0
                
                for row in rows:
                    # デバッグ: 最初の行の内容を出力
                    if day_saved == 0:
                        row_html = row.inner_html()[:400].replace("\n", " ")
                        print(f"[DEBUG] 行HTML: {row_html}", flush=True)
                    try:
                        cells = row.query_selector_all('td')
                        if len(cells) < 4:
                            continue
                        
                        # aタグのhrefから予約ID抽出
                        reserve_link = cells[2].query_selector("a[href*='reserveId=']")
                        href = reserve_link.get_attribute("href") if reserve_link else ""
                        id_match = re.search(r'reserveId=([A-Z]{2}\d+)', href)
                        booking_id = id_match.group(1) if id_match else None
                        
                        if not booking_id:
                            continue
                        
                        # 顧客名（pタグから取得）
                        name_elem = cells[2].query_selector("p.wordBreak")
                        customer_name = name_elem.text_content().strip() if name_elem else ""
                        customer_name = re.sub(r'[★☆♪♡⭐️🦁]', '', customer_name).strip()
                        
                        # 時間（"12/08\n18:00" → "18:00"だけ抽出）
                        time_cell = cells[0].text_content().strip() if len(cells) > 0 else ""
                        time_match = re.search(r'(\d{1,2}:\d{2})', time_cell)
                        time_only = time_match.group(1) if time_match else "00:00"
                        visit_datetime = f"{target_date.strftime('%Y-%m-%d')} {time_only}:00"
                        
                        # スタッフ（cells[3]）
                        staff = cells[3].text_content().strip() if len(cells) > 3 else ""
                        staff = re.sub(r'^\(指\)', '', staff).strip()
                        
                        # ソース（NET/NHPB等）
                        source = cells[4].text_content().strip() if len(cells) > 4 else ""
                        
                        if customer_name:
                            data = {
                                'booking_id': booking_id,
                                'customer_name': customer_name,
                                'phone': get_phone_for_customer(customer_name, reserve_id, session),
                                'visit_datetime': visit_datetime,
                                'menu': '',
                                'staff': staff,
                                'status': 'confirmed',
                                'booking_source': source
                            }
                            
                            res = requests.post(
                                f'{SUPABASE_URL}/rest/v1/8weeks_bookings?on_conflict=booking_id',
                                headers=headers,
                                json=data
                            )
                            
                            if res.status_code in [200, 201]:
                                total_saved += 1
                                day_saved += 1
                            else:
                                print(f"[ERROR] 保存失敗: {res.status_code} - {res.text}", flush=True)
                    except Exception as e:
                        print(f"[ERROR] 例外: {e}", flush=True)
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
