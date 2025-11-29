import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

headers = {
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}',
    'Content-Type': 'application/json'
}

# サロンボード顧客データ読み込み
with open('salonboard_customers.json', 'r', encoding='utf-8') as f:
    salonboard_customers = json.load(f)

print(f"サロンボード顧客: {len(salonboard_customers)} 件")

# 電話番号がある顧客のみ抽出
sb_with_phone = {c['phone']: c for c in salonboard_customers if c.get('phone')}
print(f"電話番号あり: {len(sb_with_phone)} 件")

# Supabase顧客データ取得
response = requests.get(
    f'{SUPABASE_URL}/rest/v1/customers?select=*',
    headers=headers
)
supabase_customers = response.json()
print(f"Supabase顧客: {len(supabase_customers)} 件")

# bookingsから電話番号を取得してマッチング
response = requests.get(
    f'{SUPABASE_URL}/rest/v1/bookings?select=customer_name,phone',
    headers=headers
)
bookings = response.json()
print(f"Bookings: {len(bookings)} 件")

# bookingsの電話番号→顧客名マッピング
booking_phone_map = {}
for b in bookings:
    if b.get('phone'):
        booking_phone_map[b['phone']] = b['customer_name']

# マッチング実行
matched = 0
updated = 0

for cust in supabase_customers:
    line_user_id = cust.get('line_user_id')
    current_name = cust.get('name', '')
    
    # 既にフルネームっぽい場合はスキップ
    if len(current_name) >= 4 and ' ' in current_name:
        continue
    
    # サロンボードデータから名前でマッチング試行
    for sb_cust in salonboard_customers:
        sb_name = sb_cust.get('name_kanji', '')
        sb_phone = sb_cust.get('phone')
        sb_customer_number = sb_cust.get('customer_number')
        
        # 名前の部分一致チェック
        if current_name in sb_name or sb_name in current_name:
            matched += 1
            print(f"マッチ: {current_name} → {sb_name} (電話: {sb_phone})")
            
            # Supabaseを更新
            update_data = {'name': sb_name}
            if sb_phone:
                update_data['phone'] = sb_phone
            if sb_customer_number:
                update_data['customer_number'] = sb_customer_number
            
            update_response = requests.patch(
                f"{SUPABASE_URL}/rest/v1/customers?line_user_id=eq.{line_user_id}",
                headers=headers,
                json=update_data
            )
            if update_response.status_code in [200, 204]:
                updated += 1
            break

print(f"\nマッチ: {matched} 件")
print(f"更新: {updated} 件")
