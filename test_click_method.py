#!/usr/bin/env python3
import os
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    login_id = os.getenv('SALONBOARD_LOGIN_ID')
    password = os.getenv('SALONBOARD_LOGIN_PASSWORD')
    
    page.goto('https://salonboard.com/login/')
    page.wait_for_selector('input[name="userId"]')
    
    page.fill('input[name="userId"]', login_id)
    page.fill('input[name="password"]', password)
    page.wait_for_timeout(1000)
    
    print("ログインボタンをクリック...")
    page.click('a.common-CNCcommon__primaryBtn.loginBtnSize', no_wait_after=True)
    
    print("URLの変化を待つ...")
    page.wait_for_url('**/KLP/**', timeout=30000)
    
    print(f"✅ ログイン成功！ URL: {page.url}")
    browser.close()
