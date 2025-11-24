# 最適化されたSALONBOARDログイン関数
import threading
from datetime import datetime
from flask import jsonify
import os

# グローバル変数：処理状態管理
login_results = {}
login_lock = threading.Lock()

@app.route('/test_salonboard_login_async', methods=['GET'])
def test_salonboard_login_async():
    """非同期SALONBOARDログインテスト"""
    task_id = datetime.now().strftime('%Y%m%d%H%M%S')
    
    # すぐにレスポンス返す
    def background_login():
        from playwright.sync_api import sync_playwright
        
        try:
            login_id = os.getenv('SALONBOARD_LOGIN_ID')
            password = os.getenv('SALONBOARD_LOGIN_PASSWORD')
            
            with sync_playwright() as p:
                # 最適化1-5: ブラウザ起動オプション
                browser = p.firefox.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        '--disable-software-rasterizer',
                        '--disable-extensions'
                    ]
                )
                
                # 最適化6-8: コンテキスト設定
                context = browser.new_context(
                    viewport={'width': 1280, 'height': 720},
                    java_script_enabled=True,
                    has_touch=False,
                    is_mobile=False,
                    bypass_csp=True
                )
                
                page = context.new_page()
                
                # 最適化9: タイムアウト短縮
                page.set_default_timeout(15000)
                
                # 最適化10: ページロード戦略
                page.goto('https://salonboard.com/login/', wait_until='domcontentloaded', timeout=15000)
                page.wait_for_selector('input[name="userId"]', timeout=10000)
                page.fill('input[name="userId"]', login_id)
                page.fill('input[name="password"]', password)
                page.press('input[name="password"]', 'Enter')
                page.wait_for_url('**/KLP/**', timeout=15000)
                
                final_url = page.url
                success = '/KLP/' in final_url
                
                browser.close()
                
                with login_lock:
                    login_results[task_id] = {
                        'success': success,
                        'message': 'ログイン成功' if success else 'ログイン失敗',
                        'final_url': final_url,
                        'timestamp': datetime.now().isoformat()
                    }
                    
        except Exception as e:
            with login_lock:
                login_results[task_id] = {
                    'success': False,
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'timestamp': datetime.now().isoformat()
                }
    
    # バックグラウンドスレッド起動
    thread = threading.Thread(target=background_login)
    thread.start()
    
    return jsonify({
        'status': 'processing',
        'task_id': task_id,
        'check_url': f'/test_salonboard_result/{task_id}',
        'message': 'ログイン処理を開始しました。結果は check_url で確認してください。'
    }), 202

@app.route('/test_salonboard_result/<task_id>', methods=['GET'])
def test_salonboard_result(task_id):
    """ログイン結果確認"""
    with login_lock:
        if task_id in login_results:
            return jsonify(login_results[task_id])
        else:
            return jsonify({
                'status': 'processing',
                'message': 'まだ処理中です。しばらくしてから再度確認してください。'
            }), 202
