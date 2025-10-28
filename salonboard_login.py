
#!/usr/bin/env python3

import sys

import json

import os

from playwright.sync_api import sync_playwright

from datetime import datetime

import time

def login_salonboard(task_id):

    result_file = f"/tmp/login_result_{task_id}.json"

    timings = {}

    

    print(f"[LOGIN_SCRIPT] 開始: {task_id}", flush=True)

    

    try:

        start = time.time()

        login_id = os.getenv('SALONBOARD_LOGIN_ID')

        password = os.getenv('SALONBOARD_LOGIN_PASSWORD')

        

        if not login_id or not password:

            raise Exception("環境変数が設定されていません")

        

        print(f"[LOGIN_SCRIPT] Playwright起動中...", flush=True)

        with sync_playwright() as p:

            timings['playwright_start'] = round(time.time() - start, 2)

            

            print(f"[LOGIN_SCRIPT] Firefox起動中...", flush=True)

            step_start = time.time()

            browser = p.chromium.launch(

                headless=True,

                args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu']

            )

            timings['browser_launch'] = round(time.time() - step_start, 2)

            

            print(f"[LOGIN_SCRIPT] ページ作成中...", flush=True)

            step_start = time.time()

            page = browser.new_page()

            

            # ⏱️ タイムアウトを180秒に延長

            page.set_default_timeout(180000)

            

            page.route("**/*.{png,jpg,jpeg,gif,svg,css,woff,woff2}", lambda route: route.abort())

            timings['page_create'] = round(time.time() - step_start, 2)

            

            print(f"[LOGIN_SCRIPT] ログインページ移動中...", flush=True)

            step_start = time.time()

            page.goto('https://salonboard.com/login/', wait_until='domcontentloaded', timeout=180000)

            timings['page_goto'] = round(time.time() - step_start, 2)

            print(f"[LOGIN_SCRIPT] ページ読み込み: {timings['page_goto']}秒", flush=True)

            

            print(f"[LOGIN_SCRIPT] フォーム待機中...", flush=True)

            step_start = time.time()

            page.wait_for_selector('input[name="userId"]', timeout=30000)

            timings['wait_selector'] = round(time.time() - step_start, 2)

            

            print(f"[LOGIN_SCRIPT] ログイン情報入力中...", flush=True)

            page.fill('input[name="userId"]', login_id)

            page.fill('input[name="password"]', password)

            page.press('input[name="password"]', 'Enter')

            

            print(f"[LOGIN_SCRIPT] ログイン遷移待機中...", flush=True)

            step_start = time.time()

            page.wait_for_url('**/KLP/**', timeout=180000)

            timings['wait_url'] = round(time.time() - step_start, 2)

            print(f"[LOGIN_SCRIPT] ログイン成功: {timings['wait_url']}秒", flush=True)

            

            final_url = page.url

            timings['total'] = round(time.time() - start, 2)

            

            browser.close()

            

            result = {

                'success': True,

                'url': final_url,

                'timings': timings,

                'timestamp': datetime.now().isoformat()

            }

            print(f"[LOGIN_SCRIPT] 完了: 合計{timings['total']}秒", flush=True)

            

    except Exception as e:

        print(f"[LOGIN_SCRIPT] エラー: {type(e).__name__}: {str(e)}", flush=True)

        import traceback

        print(f"[LOGIN_SCRIPT] traceback:\n{traceback.format_exc()}", flush=True)

        result = {

            'success': False,

            'error': str(e),

            'error_type': type(e).__name__,

            'timings': timings,

            'timestamp': datetime.now().isoformat()

        }

    

    with open(result_file, 'w') as f:

        json.dump(result, f)

    

    print(json.dumps(result), flush=True)

if __name__ == '__main__':

    task_id = sys.argv[1]

    login_salonboard(task_id)

