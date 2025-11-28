#!/usr/bin/env python3
"""
Macで定期的にクッキーを更新するスクリプト
launchdで週1回実行
"""
import subprocess
import json
from datetime import datetime
from playwright.sync_api import sync_playwright

def update_cookies():
    print(f"[{datetime.now()}] クッキー自動更新開始")
    
    try:
        with sync_playwright() as p:
            # 既存のクッキーでログイン試行
            browser = p.chromium.launch(headless=True)
            
            with open('session_cookies.json', 'r') as f:
                cookies = json.load(f)
            
            context = browser.new_context()
            context.add_cookies(cookies)
            page = context.new_page()
            
            # ログイン状態確認
            page.goto('https://salonboard.com/KLP/reserve/reserveList/', timeout=30000)
            page.wait_for_timeout(3000)
            
            if 'login' in page.url.lower():
                print("ログイン切れ - 手動更新が必要")
                # 通知を送る（LINE等）
                browser.close()
                return False
            
            # クッキー更新
            new_cookies = context.cookies()
            with open('session_cookies.json', 'w') as f:
                json.dump(new_cookies, f, indent=2, ensure_ascii=False)
            
            print(f"クッキー更新成功: {len(new_cookies)}個")
            browser.close()
            
            # GitHubにプッシュ
            subprocess.run(['git', 'add', 'session_cookies.json'], cwd='/Users/kanbararyousuke/salon-absence-system')
            subprocess.run(['git', 'commit', '-m', 'Auto update cookies'], cwd='/Users/kanbararyousuke/salon-absence-system')
            subprocess.run(['git', 'push'], cwd='/Users/kanbararyousuke/salon-absence-system')
            
            # VPSにコピー
            subprocess.run(['scp', 'session_cookies.json', 'ubuntu@153.120.1.43:~/'], cwd='/Users/kanbararyousuke/salon-absence-system')
            
            print(f"[{datetime.now()}] 完了")
            return True
            
    except Exception as e:
        print(f"エラー: {e}")
        return False

if __name__ == "__main__":
    update_cookies()
