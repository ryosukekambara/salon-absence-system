#!/usr/bin/env python3
"""Renderからサロンボードにアクセスできるかテスト"""
import os
from playwright.sync_api import sync_playwright

def test_login():
    login_id = os.environ.get('SALONBOARD_LOGIN_ID', 'CD18317')
    login_password = os.environ.get('SALONBOARD_LOGIN_PASSWORD', 'Ne8T2Hhi!')
    
    print(f"[TEST] ログインID: {login_id[:2]}***")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print("[1] ログインページにアクセス...")
        page.goto('https://salonboard.com/login/', timeout=60000)
        page.wait_for_timeout(3000)
        print(f"    URL: {page.url}")
        
        print("[2] ID入力...")
        page.fill('input[name="userId"]', login_id)
        page.wait_for_timeout(500)
        
        print("[3] パスワード入力...")
        page.fill('input[name="password"]', login_password)
        page.wait_for_timeout(500)
        
        print("[4] ログインボタンクリック...")
        page.click('a:has-text("ログイン")')
        page.wait_for_timeout(10000)
        
        print(f"[5] 現在のURL: {page.url}")
        
        if 'login' not in page.url.lower():
            print("✅ ログイン成功！RenderからサロンボードにアクセスOK！")
            result = "SUCCESS"
        else:
            print("❌ ログイン失敗。IPがブロックされている可能性。")
            result = "FAILED"
        
        browser.close()
        return result

if __name__ == "__main__":
    test_login()
