
@app.route('/test_async', methods=['GET'])
def test_async():
    """subprocess版非同期ログインテスト"""
    import subprocess
    task_id = datetime.now().strftime('%Y%m%d%H%M%S%f')
    
    def bg_login():
        try:
            print(f"[SUBPROCESS] タスク開始: {task_id}", flush=True)
            
            # 完全に独立したプロセスとして実行
            result = subprocess.run(
                ['python3', 'salonboard_login.py', task_id],
                capture_output=True,
                text=True,
                timeout=60,
                env=os.environ.copy()
            )
            
            print(f"[SUBPROCESS] stdout: {result.stdout}", flush=True)
            print(f"[SUBPROCESS] stderr: {result.stderr}", flush=True)
            
            # 結果ファイルから読み込み
            result_file = f"/tmp/login_result_{task_id}.json"
            if os.path.exists(result_file):
                with open(result_file, 'r') as f:
                    result_data = json.load(f)
                with login_lock:
                    login_results[task_id] = result_data
                os.remove(result_file)
            else:
                with login_lock:
                    login_results[task_id] = {
                        'success': False,
                        'error': 'Result file not found',
                        'stdout': result.stdout,
                        'stderr': result.stderr
                    }
                    
        except Exception as e:
            print(f"[SUBPROCESS] エラー: {str(e)}", flush=True)
            with login_lock:
                login_results[task_id] = {
                    'success': False,
                    'error': str(e),
                    'error_type': type(e).__name__
                }
    
    threading.Thread(target=bg_login, daemon=True).start()
    return jsonify({
        'status': 'processing',
        'task_id': task_id,
        'check_url': f'/result/{task_id}',
        'message': 'subprocess版ログイン処理を開始しました'
    }), 202
