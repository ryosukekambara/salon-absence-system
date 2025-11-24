
@app.route('/test_async', methods=['GET'])
def test_async():
    """非同期ログインテスト（ログ・エラー詳細付き）"""
    task_id = datetime.now().strftime('%Y%m%d%H%M%S%f')
    
    def bg_login():
        import time
        import traceback
        from playwright.sync_api import sync_playwright
        
        timings = {}
        current_step = 'init'
        
        try:
            start_total = time.time()
            
            # ステップ1: Playwright起動
            current_step = 'playwright_start'
            step_start = time.time()
            p = sync_playwright().start()
            timings['playwright_start'] = round(time.time() - step_start, 2)
            
            # ステップ2: ブラウザ起動
            current_step = 'browser_launch'
            step_start = time.time()
            browser = p.firefox.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
            timings['browser_launch'] = round(time.time() - step_start, 2)
            
            # ステップ3: ページ作成
            current_step = 'page_create'
            step_start = time.time()
            page = browser.new_page()
            page.set_default_timeout(15000)
            timings['page_create'] = round(time.time() - step_start, 2)
            
            # ステップ4: ページ移動
            current_step = 'page_goto'
            step_start = time.time()
            page.goto('https://salonboard.com/login/', wait_until='domcontentloaded', timeout=15000)
            timings['page_goto'] = round(time.time() - step_start, 2)
            
            # ステップ5: フォーム待機
            current_step = 'wait_selector'
            step_start = time.time()
            page.wait_for_selector('input[name="userId"]', timeout=10000)
            timings['wait_selector'] = round(time.time() - step_start, 2)
            
            # ステップ6: 入力
            current_step = 'fill_form'
            step_start = time.time()
            page.fill('input[name="userId"]', os.getenv('SALONBOARD_LOGIN_ID'))
            page.fill('input[name="password"]', os.getenv('SALONBOARD_LOGIN_PASSWORD'))
            timings['fill_form'] = round(time.time() - step_start, 2)
            
            # ステップ7: 送信
            current_step = 'submit'
            step_start = time.time()
            page.press('input[name="password"]', 'Enter')
            timings['submit'] = round(time.time() - step_start, 2)
            
            # ステップ8: 遷移待機
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
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            with login_lock:
                login_results[task_id] = {
                    'success': False,
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'failed_at_step': current_step,
                    'timings': timings,
                    'traceback': traceback.format_exc(),
                    'timestamp': datetime.now().isoformat()
                }
    
    threading.Thread(target=bg_login, daemon=True).start()
    return jsonify({
        'status': 'processing',
        'task_id': task_id,
        'check_url': f'/result/{task_id}',
        'message': 'ログイン処理を開始しました。30-60秒後に check_url で結果を確認してください。'
    }), 202
