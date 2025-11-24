#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# Supabase接続
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)

# 顧客データ取得（最初の5件をサンプル表示）
response = supabase.table('customers').select('*').limit(5).execute()

print("=== Supabaseデータサンプル ===")
for customer in response.data:
    print(customer)
    print("---")

print(f"\n合計件数: {len(response.data)}件")
