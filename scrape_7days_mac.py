#!/usr/bin/env python3
import json
import re
from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    
    with open('session_cookies.json', 'r') as f:
        cookies = json.load(f)
    
    context = browser.new_context()
    context.add_cookies(cookies)
    page = context.new_page()
    
    today = (datetime.now() + timedelta(days=7)).strftime('%Y%m%d')
    url = f'https://salonboard.com/KLP/reserve/reserveList/searchDate?date={today}'
    
    print(f"[SCRAPE] 本日の予約にアクセス（{today}）...")
    page.goto(url, timeout=90000)
    page.wait_for_timeout(3000)
    
    # 第1段階：予約IDと基本情報を取得
    basic_bookings = []
    seen_ids = set()
    rows = page.query_selector_all('table tbody tr')
    print(f"[SCRAPE] {len(rows)}行を検出")
    
    for row in rows:
        try:
            cells = row.query_selector_all('td')
            if len(cells) < 4:
                continue
            
            datetime_text = cells[0].text_content().strip()
            status = cells[1].text_content().strip()
            customer_name = cells[2].text_content().strip()
            
            if datetime_text.isdigit() or 'キャンセル' in status:
                continue
            if not datetime_text or not customer_name:
                continue
            
            id_match = re.search(r'\(([A-Z]{2}\d+)\)', customer_name)
            booking_id = id_match.group(1) if id_match else None
            
            if not booking_id or booking_id in seen_ids:
                continue
            seen_ids.add(booking_id)
            
            staff = cells[3].text_content().strip() if len(cells) > 3 else ""
            source = cells[4].text_content().strip() if len(cells) > 4 else ""
            menu = cells[5].text_content().strip() if len(cells) > 5 else ""
            
            basic_bookings.append({
                "来店日時": datetime_text,
                "ステータス": status,
                "お客様名": customer_name,
                "スタッフ": staff,
                "予約経路": source,
                "メニュー": menu,
                "予約ID": booking_id
            })
        except Exception as e:
            continue
    
    print(f"[SCRAPE] {len(basic_bookings)}件の予約IDを取得")
    
    # 第2段階：各予約の詳細から電話番号とお客様番号を取得
    bookings = []
    for i, booking in enumerate(basic_bookings):
        try:
            booking_id = booking["予約ID"]
            source = booking["予約経路"]
            print(f"[SCRAPE] ({i+1}/{len(basic_bookings)}) {booking['お客様名'][:20]}の詳細取得中...")
            
            # 予約経路に応じてURLを切り替え
            if source == "NHPB":
                detail_url = f'https://salonboard.com/KLP/reserve/net/reserveDetail/?reserveid={booking_id}'
            else:
                detail_url = f'https://salonboard.com/KLP/reserve/ext/extReserveDetail/?reserveid={booking_id}'
            
            page.goto(detail_url)
            page.wait_for_timeout(2000)
            
            # 電話番号を取得
            phone_cell = page.query_selector('tr:has-text("電話番号") td:nth-child(2)')
            phone = phone_cell.text_content().strip() if phone_cell else ""
            
            # 電話番号から数字のみ抽出（余計なテキストを除去）
            phone_match = re.search(r'(0\d{9,10})', phone)
            phone = phone_match.group(1) if phone_match else phone
            
            # お客様番号を取得
            customer_number_cell = page.query_selector('tr:has-text("お客様番号") td:nth-child(2)')
            customer_number = customer_number_cell.text_content().strip() if customer_number_cell else ""
            
            booking["電話番号"] = phone
            booking["お客様番号"] = customer_number
            bookings.append(booking)
            print(f"[SCRAPE] 取得完了: {phone} / 番号:{customer_number} ({source})")
            
        except Exception as e:
            print(f"[ERROR] {booking_id}: {e}")
            booking["電話番号"] = ""
            booking["お客様番号"] = ""
            bookings.append(booking)
    
    browser.close()
    
    result = {
        "success": True,
        "bookings": bookings,
        "count": len(bookings),
        "date": today,
        "timestamp": datetime.now().isoformat()
    }
    
    result_file = f"scrape_result_7days.json"
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n[SCRAPE] 完了: {len(bookings)}件の予約を取得（電話番号+お客様番号付き）")
    print(f"[SCRAPE] 結果ファイル: {result_file}")
