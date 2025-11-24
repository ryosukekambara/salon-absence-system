#!/usr/bin/env python3
import os
import json
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)

# スクレイピング結果を読み込み
with open('scrape_result_with_phone_20251111_212809.json') as f:
    scrape_data = json.load(f)

print(f"=== スクレイピング結果: {scrape_data['count']}件 ===")

# Supabaseの全顧客を取得
customers = supabase.table('customers').select('*').execute()
print(f"=== Supabase顧客: {len(customers.data)}件 ===\n")

# 電話番号でマッチング
matched = 0
for booking in scrape_data['bookings']:
    phone = booking['電話番号']
    if not phone:
        continue
    
    # Supabaseから電話番号で検索
    # （まだ電話番号カラムがないので、手動で追加が必要）
    print(f"予約ID: {booking['予約ID']} - 電話番号: {phone}")

print(f"\n合計: {matched}件マッチング")
