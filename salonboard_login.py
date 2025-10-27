#!/usr/bin/env python3
import sys
import json
import os
from playwright.sync_api import sync_playwright
from datetime import datetime
import time

def login_salonboard(task_id):
    """完全に独立したプロセスでSALONBOARDログイン"""
    result_file = f"/tmp/login_result_{task_id}.json"
    
    timings = {}
    try:
        start = time.time()
        
        login_id = os.getenv('SALONBOARD_LOGIN_ID')
        password = os.getenv('SALONBOARD_LOGIN_PASSWORD')
        
        with sync_playwright() as p:
            timings['playwright_start'] = time.time() - start
            
            step_start = time.time()
            browser = p.firefox.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
            )
            timings['browser_launch'] = time.time() - step_start
            
            step_start = time.time()
            page = browser.new_page()
            page.set_default_timeout(15000)
            page.route("**/*.{png,jpg,jpeg,gif,svg,css,woff,woff2}", lambda route: route.abort())
            timings['page_create'] = time.time() - step_start
            
            step_start = time.time()
            page.goto('https://salonboard.com/login/', wait_until='domcontentloaded', timeout=15000)
            timings['page_goto'] = time.time() - step_start
            
            step_start = time.time()
            page.wait_for_selector('input[name="userId"]', timeout=10000)
            timings['wait_selector'] = time.time() - step_start
            
            page.fill('input[name="userId"]', login_id)
            page.fill('input[name="password"]', password)
            page.press('input[name="password"]', 'Enter')
            
            step_start = time.time()
            page.wait_for_url('**/KLP/**', timeout=15000)
            timings['wait_url'] = time.time() - step_start
            
            final_url = page.url
            timings['total'] = time.time() - start
            
            browser.close()
            
            result = {
                'success': True,
                'url': final_url,
                'timings': {k: round(v, 2) for k, v in timings.items()},
                'timestamp': datetime.now().isoformat()
            }
            
    except Exception as e:
        result = {
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__,
            'timings': {k: round(v, 2) for k, v in timings.items()},
            'timestamp': datetime.now().isoformat()
        }
    
    with open(result_file, 'w') as f:
        json.dump(result, f)
    
    print(json.dumps(result))

if __name__ == '__main__':
    task_id = sys.argv[1]
    login_salonboard(task_id)
