
def bg_login():
    import time
    import traceback
    from playwright.sync_api import sync_playwright
    
    max_retries = 3
    retry_count = 0
    timings = {}
    current_step = 'init'
    
    while retry_count < max_retries:
        try:
            start_total = time.time()
            
            current_step = 'playwright_start'
            step_start = time.time()
            p = sync_playwright().start()
            timings['playwright_start'] = round(time.time() - step_start, 2)
            
            current_step = 'browser_launch'
            step_start = time.time()
            browser = p.firefox.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
            timings['browser_launch'] = round(time.time() - step_start, 2)
            
            current_step = 'page_create'
            step_start = time.time()
            page = browser.new_page()
            page.set_default_timeout(15000)
            timings['page_create'] = round(time.time() - step_start, 2)
            
            current_step = 'page_goto'
            step_start = time.time()
            page.goto('https://salonboard.com/login/', wait_until='domcontentloaded', timeout=15000)
            timings['page_goto'] = round(time.time() - step_start, 2)
            
            current_step = 'wait_selector'
            step_start = time.time()
            page.wait_for_selector('input[name="userId"]', timeout=10000)
            timings['wait_selector'] = round(time.time() - step_start, 2)
            
            current_step = 'fill_form'
            step_start = time.time()
            page.fill('input[name="userId"]', os.getenv('SALONBOARD_LOGIN_ID'))
            page.fill('input[name="password"]', os.getenv('SALONBOARD_LOGIN_PASSWORD'))
            timings['fill_form'] = round(time.time() - step_start, 2)
            
            current_step = 'submit'
            step_start = time.time()
            page.press('input[name="password"]', 'Enter')
            timings['submit'] = round(time.time() - step_start, 2)
            
            current_step = 'wait_url'
            step_start = time.time()
            page.wait_for_url('**/KLP/**', timeout=15000)
            timings['wait_url'] = round(time.time() - step_start, 2)
            
            final_url = page.url
            timings['total'] = round(time.time() - start_total, 2)
            
            browser.close()
            p.stop()
            
            with login_lock:
                login_results[task_id] = {
                    'success': True,
                    'url': final_url,
                    'timings': timings,
                    'retry_count': retry_count,
                    'timestamp': datetime.now().isoformat()
                }
            return  # 成功したら終了
            
        except Exception as e:
            retry_count += 1
            if retry_count >= max_retries:
                # 最終失敗
                with login_lock:
                    login_results[task_id] = {
                        'success': False,
                        'error': str(e),
                        'error_type': type(e).__name__,
                        'failed_at_step': current_step,
                        'timings': timings,
                        'retry_count': retry_count,
                        'traceback': traceback.format_exc(),
                        'timestamp': datetime.now().isoformat()
                    }
            else:
                # リトライ待機
                time.sleep(2)
