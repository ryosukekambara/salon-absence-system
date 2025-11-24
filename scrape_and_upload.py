#!/usr/bin/env python3
import asyncio
import subprocess
import json
from datetime import datetime, timedelta
import os

async def main():
    print(f"[{datetime.now()}] スクレイピング開始")
    
    # 3日後と7日後の日付
    date_3days = (datetime.now() + timedelta(days=3)).strftime("%Y%m%d")
    date_7days = (datetime.now() + timedelta(days=7)).strftime("%Y%m%d")
    
    print(f"対象日付: 3日後={date_3days}, 7日後={date_7days}")
    
    # スクレイピング実行（既存のスクリプト使用）
    result_3 = subprocess.run([
        "python3", "scrape_3days_mac.py"
    ], capture_output=True, text=True)
    
    result_7 = subprocess.run([
        "python3", "scrape_7days_mac.py"
    ], capture_output=True, text=True)
    
    # VPSに転送
    vps_ip = "153.120.1.43"
    
    subprocess.run([
        "scp",
        f"scrape_result_3days.json",
        f"ubuntu@{vps_ip}:~/"
    ])
    
    subprocess.run([
        "scp",
        f"scrape_result_7days.json",
        f"ubuntu@{vps_ip}:~/"
    ])
    
    print(f"[{datetime.now()}] 完了")
    return {"success": True, "message": "スクレイピング完了"}

if __name__ == "__main__":
    result = asyncio.run(main())
    print(json.dumps(result, ensure_ascii=False))
