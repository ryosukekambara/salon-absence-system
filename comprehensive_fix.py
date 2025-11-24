    def bg_login():
        import time
        import traceback
        import sys
        import subprocess
        from playwright.sync_api import sync_playwright
        
        print(f"[BG_LOGIN] タスク開始: {task_id}", flush=True)
        print(f"[BG_LOGIN] Python: {sys.version}", flush=True)
        print(f"[BG_LOGIN] メモリ情報確認中...", flush=True)
        
        # メモリ確認
        try:
            mem_info = subprocess.run(['free', '-h'], capture_output=True, text=True, timeout=5)
            print(f"[BG_LOGIN] メモリ:\n{mem_info.stdout}", flush=True)
        except:
            pass
        
        max_retries = 3
        retry_count = 0
        timings = {}
        current_step = 'init'
        
        while retry_count < max_retries:
            try:
                start_total = time.time()
                
                current_step = 'env_check'
                print(f"[BG_LOGIN] 環境変数確認", flush=True)
                login_id = os.getenv('SALONBOARD_LOGIN_ID')
                password = os.getenv('SALONBOARD_LOGIN_PASSWORD')
                if not login_id or not password:
                    raise Exception("環境変数が設定されていません")
                
                current_step = 'playwright_start'
                print(f"[BG_LOGIN] Playwright起動中...", flush=True)
                step_start = time.time()
                p = sync_playwright().start()
                timings['playwright_start'] = round(time.time() - step_start, 2)
                print(f"[BG_LOGIN] Playwright起動完了 ({timings['playwright_start']}秒)", flush=True)
                
                current_step = 'browser_launch'
                print(f"[BG_LOGIN] Firefox起動中（メモリ最適化モード）...", flush=True)
                step_start = time.time()
                
                # 包括的なブラウザ起動オプション
                browser = p.firefox.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        '--disable-software-rasterizer',
                        '--disable-extensions',
                        '--disable-background-networking',
                        '--disable-sync',
                        '--metrics-recording-only',
                        '--no-first-run',
                    ],
                    firefox_user_prefs={
                        'browser.cache.disk.enable': False,
                        'browser.cache.memory.enable': False,
                        'permissions.default.image': 2,  # 画像無効化
                    }
                )
                timings['browser_launch'] = round(time.time() - step_start, 2)
                print(f"[BG_LOGIN] Firefox起動完了 ({timings['browser_launch']}秒)", flush=True)
                
                current_step = 'context_create'
                step_start = time.time()
                context = browser.new_context(
                    viewport={'width': 1280, 'height': 720},
                    user_agent='Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0',
                    java_script_enabled=True,
                    bypass_csp=True,
                )
                timings['context_create'] = round(time.time() - step_start, 2)
                
                current_step = 'page_create'
                step_start = time.time()
                page = context.new_page()
                page.set_default_timeout(15000)
                
                # リソースブロック
                page.route("**/*.{png,jpg,jpeg,gif,svg,css,woff,woff2,ttf,eot}", lambda route: route.abort())
                
                timings['page_create'] = round(time.time() - step_start, 2)
                
                current_step = 'page_goto'
                print(f"[BG_LOGIN] ページ移動中...", flush=True)
                step_start = time.time()
                page.goto('https://salonboard.com/login/', wait_until='domcontentloaded', timeout=15000)
                timings['page_goto'] = round(time.time() - step_start, 2)
                print(f"[BG_LOGIN] ページ読み込み完了 ({timings['page_goto']}秒)", flush=True)
                
                current_step = 'wait_selector'
                print(f"[BG_LOGIN] フォーム待機中...", flush=True)
                step_start = time.time()
                page.wait_for_selector('input[name="userId"]', timeout=10000)
                timings['wait_selector'] = round(time.time() - step_start, 2)
                
                current_step = 'fill_form'
                step_start = time.time()
                page.fill('input[name="userId"]', login_id)
                page.fill('input[name="password"]', password)
                timings['fill_form'] = round(time.time() - step_start, 2)
                
                current_step = 'submit'
                step_start = time.time()
                page.press('input[name="password"]', 'Enter')
                timings['submit'] = round(time.time() - step_start, 2)
                
                current_step = 'wait_url'
                print(f"[BG_LOGIN] ログイン遷移待機中...", flush=True)
                step_start = time.time()
                page.wait_for_url('**/KLP/**', timeout=15000)
                timings['wait_url'] = round(time.time() - step_start, 2)
                
                final_url = page.url
                timings['total'] = round(time.time() - start_total, 2)
                
                print(f"[BG_LOGIN] 成功！結果を保存 (合計{timings['total']}秒)", flush=True)
                
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
                return
                
            except Exception as e:
                retry_count += 1
                error_msg = f"{type(e).__name__}: {str(e)}"
                print(f"[BG_LOGIN] エラー at {current_step}: {error_msg}", flush=True)
                print(f"[BG_LOGIN] リトライ {retry_count}/{max_retries}", flush=True)
                
                if retry_count >= max_retries:
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
                    print(f"[BG_LOGIN] 最終失敗: {error_msg}", flush=True)
                else:
                    time.sleep(2)
                    
                # ブラウザクリーンアップ
                try:
                    if 'browser' in locals():
                        browser.close()
                    if 'p' in locals():
                        p.stop()
                except:
                    pass
    
