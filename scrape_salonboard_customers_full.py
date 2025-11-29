import json
import requests
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv
import time

load_dotenv()

with open('session_cookies.json', 'r') as f:
    cookies_list = json.load(f)

cookies = {c['name']: c['value'] for c in cookies_list}

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
}

def get_customer_detail(customer_id):
    """顧客詳細ページから電話番号を取得"""
    url = f"https://salonboard.com/KLP/customer/customerDetail/?customerId={customer_id}"
    response = requests.get(url, cookies=cookies, headers=headers)
    
    if response.status_code != 200:
        return None, None
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    phone = None
    customer_no = None
    
    for row in soup.select('table tr'):
        th = row.find('th')
        td = row.find('td')
        if th and td:
            label = th.get_text(strip=True)
            value = td.get_text(strip=True)
            if '電話番号1' in label and value != '-':
                phone = value
            if 'お客様番号' in label and value != '-':
                customer_no = value
    
    return phone, customer_no

# 既存のデータを読み込み
with open('salonboard_customers.json', 'r', encoding='utf-8') as f:
    customers = json.load(f)

print(f"合計 {len(customers)} 件の顧客データを処理します")
print("電話番号を取得中... (約30分かかります)")

for i, cust in enumerate(customers):
    if i % 50 == 0:
        print(f"進捗: {i}/{len(customers)} ({i*100//len(customers)}%)")
    
    phone, cust_no = get_customer_detail(cust['customer_id'])
    cust['phone'] = phone
    if cust_no:
        cust['customer_number'] = cust_no
    
    time.sleep(0.5)
    
    # 100件ごとに途中保存
    if i % 100 == 0 and i > 0:
        with open('salonboard_customers.json', 'w', encoding='utf-8') as f:
            json.dump(customers, f, ensure_ascii=False, indent=2)

# 最終保存
with open('salonboard_customers.json', 'w', encoding='utf-8') as f:
    json.dump(customers, f, ensure_ascii=False, indent=2)

print(f"\n完了! {len(customers)} 件を保存しました")

# 電話番号がある件数をカウント
with_phone = sum(1 for c in customers if c.get('phone'))
print(f"電話番号あり: {with_phone} 件")
