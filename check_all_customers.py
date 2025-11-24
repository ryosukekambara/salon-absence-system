#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)

# 全顧客データ取得
response = supabase.table('customers').select('*').execute()

print(f"=== 全顧客データ（{len(response.data)}件） ===")

# customer_numberが入っているデータを探す
has_customer_number = [c for c in response.data if c.get('customer_number')]

print(f"customer_numberあり: {len(has_customer_number)}件")
print(f"customer_numberなし: {len(response.data) - len(has_customer_number)}件")

if has_customer_number:
    print("\n【customer_numberがあるデータ例】")
    for c in has_customer_number[:3]:
        print(f"  {c['name']} → {c['customer_number']}")
else:
    print("\n⚠️ すべてのデータでcustomer_numberがNullです")
    print("\n【顧客名の例（最初の10件）】")
    for c in response.data[:10]:
        print(f"  - {c['name']} (LINE: {c['line_user_id'][:20]}...)")
