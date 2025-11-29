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

def scrape_customer_page(page_num):
    url = f"https://salonboard.com/KLP/customer/customerSearch/search?pn={page_num}"
    response = requests.get(url, cookies=cookies, headers=headers)
    
    if response.status_code != 200:
        print(f"ページ {page_num} 取得失敗: {response.status_code}")
        return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    customers = []
    
    for row in soup.select('tbody tr.mod_middle'):
        cells = row.find_all('td')
        if len(cells) >= 6:
            link = cells[0].find('a')
            if link:
                customer_id = link.get('data-customerId', '')
                name_kana = link.get_text(strip=True).replace('\xa0', ' ')
                name_kanji = cells[1].get_text(strip=True).replace('\xa0', ' ').replace('★', '')
                customer_number = cells[2].get_text(strip=True)
                if customer_number == '-':
                    customer_number = None
                
                customers.append({
                    'customer_id': customer_id,
                    'name_kana': name_kana,
                    'name_kanji': name_kanji,
                    'customer_number': customer_number
                })
    
    return customers

def get_customer_detail(customer_id):
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

# 全ページをスクレイピング
all_customers = []
total_pages = 28

for page in range(1, total_pages + 1):
    print(f"ページ {page}/{total_pages} を取得中...")
    customers = scrape_customer_page(page)
    
    for i, cust in enumerate(customers):
        print(f"  詳細取得中: {cust['name_kanji']} ({i+1}/{len(customers)})")
        phone, cust_no = get_customer_detail(cust['customer_id'])
        cust['phone'] = phone
        if cust_no:
            cust['customer_number'] = cust_no
        time.sleep(0.5)
    
    all_customers.extend(customers)
    print(f"  -> {len(customers)} 件完了 (累計: {len(all_customers)})")
    
    # ページごとに途中保存
    with open('salonboard_customers.json', 'w', encoding='utf-8') as f:
        json.dump(all_customers, f, ensure_ascii=False, indent=2)

print(f"\n合計: {len(all_customers)} 件")
print("salonboard_customers.json に保存しました")

with_phone = sum(1 for c in all_customers if c.get('phone'))
print(f"電話番号あり: {with_phone} 件")
