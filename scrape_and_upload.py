#!/usr/bin/env python3
import asyncio
import subprocess
import json
from datetime import datetime, timedelta
import os
import requests

async def main():
    print(f"[{datetime.now()}] スクレイピング開始")
    
    # 3日後と7日後の日付
    today = datetime.now()
    date_3days = (today + timedelta(days=3)).strftime("%Y%m%d")
    date_7days = (today + timedelta(days=7)).strftime("%Y%m%d")
    
    print(f"対象日付: 3日後={date_3days}, 7日後={date_7days}")
    
    # スクレイピング実行
    result_3 = subprocess.run([
        "python3", "scrape_3days_mac.py"
    ], capture_output=True, text=True)
    print(f"3日後スクレイピング結果: {result_3.stdout}")
    if result_3.stderr:
        print(f"3日後エラー: {result_3.stderr}")
    
    result_7 = subprocess.run([
        "python3", "scrape_7days_mac.py"
    ], capture_output=True, text=True)
    print(f"7日後スクレイピング結果: {result_7.stdout}")
    if result_7.stderr:
        print(f"7日後エラー: {result_7.stderr}")
    
    # Supabaseに保存
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        print("エラー: Supabase環境変数が設定されていません")
        return {"success": False, "message": "Supabase未設定"}
    
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    
    # 3日後のデータを読み込み
    try:
        with open("scrape_result_3days.json", "r") as f:
            data_3days_content = json.load(f)
    except Exception as e:
        print(f"3日後ファイル読み込みエラー: {e}")
        data_3days_content = []
    
    # 7日後のデータを読み込み
    try:
        with open("scrape_result_7days.json", "r") as f:
            data_7days_content = json.load(f)
    except Exception as e:
        print(f"7日後ファイル読み込みエラー: {e}")
        data_7days_content = []
    
    # 3日後のデータをSupabaseに保存
    data_3days = {
        "scrape_date": today.strftime("%Y-%m-%d"),
        "days_ahead": 3,
        "booking_data": data_3days_content
    }
    
    response_3 = requests.post(
        f"{supabase_url}/rest/v1/salon_bookings",
        headers=headers,
        json=data_3days
    )
    
    print(f"3日後Supabase保存: {response_3.status_code}")
    if response_3.status_code not in [200, 201]:
        print(f"3日後保存エラー: {response_3.text}")
    
    # 7日後のデータをSupabaseに保存
    data_7days = {
        "scrape_date": today.strftime("%Y-%m-%d"),
        "days_ahead": 7,
        "booking_data": data_7days_content
    }
    
    response_7 = requests.post(
        f"{supabase_url}/rest/v1/salon_bookings",
        headers=headers,
        json=data_7days
    )
    
    print(f"7日後Supabase保存: {response_7.status_code}")
    if response_7.status_code not in [200, 201]:
        print(f"7日後保存エラー: {response_7.text}")
    
    print(f"[{datetime.now()}] 完了")
    return {"success": True, "message": "スクレイピング完了、Supabaseに保存"}

if __name__ == "__main__":
    result = asyncio.run(main())
    print(json.dumps(result, ensure_ascii=False))
