from flask import Flask, request, jsonify, render_template_string, redirect, session, flash
from datetime import datetime
import json

app = Flask(__name__)
app.secret_key = 'salon-management-secret-2025'

# データストレージ
staff_data = {
    "staff001": {
        "name": "田中美咲", 
        "password": "pass123", 
        "skills": ["カット", "カラー"], 
        "phone": "090-1111-1111",
        "role": "スタイリスト"
    },
    "admin": {
        "name": "管理者", 
        "password": "admin123", 
        "skills": ["管理"], 
        "phone": "090-0000-0000",
        "role": "管理者"
    }
}

@app.route('/')
def dashboard():
    if 'logged_in' not in session:
        return redirect('/login')
    
    return f"""
    <html>
    <head><title>サロン管理システム</title></head>
    <body style="font-family: Arial; padding: 20px; background: #f5f5f5;">
        <h1>ダッシュボード</h1>
        <p>ようこそ、{session.get('user_name')}さん</p>
        <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h2>システム状態</h2>
            <p>✅ ログイン成功</p>
            <p>✅ セッション有効</p>
            <p>✅ システム稼働中</p>
        </div>
        <a href="/logout" style="background: #f44336; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">ログアウト</a>
    </body>
    </html>
    """

@app.route('/login', methods=['GET', 'POST'])
def login():
    error_message = ""
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        # 入力バリデーション
        if not username or not password:
            error_message = "IDとパスワードを入力してください"
        elif username in staff_data and staff_data[username]['password'] == password:
            session['logged_in'] = True
            session['user'] = username
            session['user_name'] = staff_data[username]['name']
            return redirect('/')
        else:
            error_message = "IDまたはパスワードが間違っています"
    
    login_template = """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ログイン - サロン管理システム</title>
        <style>
            body {
                font-family: 'Hiragino Sans', 'Yu Gothic', Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
                padding: 20px;
                box-sizing: border-box;
            }
            .login-container {
                background: white;
                padding: 40px;
                border-radius: 15px;
                box-shadow: 0 15px 35px rgba(0,0,0,0.2);
                width: 100%;
                max-width: 400px;
                animation: slideUp 0.5s ease-out;
            }
            @keyframes slideUp {
                from { transform: translateY(30px); opacity: 0; }
                to { transform: translateY(0); opacity: 1; }
            }
            .logo {
                text-align: center;
                margin-bottom: 30px;
            }
            .logo h1 {
                color: #4CAF50;
                margin: 0;
                font-size: 2em;
            }
            .logo p {
                color: #666;
                margin: 8px 0 0 0;
                font-size: 14px;
            }
            .form-group {
                margin-bottom: 20px;
            }
            label {
                display: block;
                margin-bottom: 8px;
                font-weight: bold;
                color: #333;
                font-size: 14px;
            }
            input[type="text"], input[type="password"] {
                width: 100%;
                padding: 15px;
                border: 2px solid #e0e0e0;
                border-radius: 10px;
                box-sizing: border-box;
                font-size: 16px;
                transition: all 0.3s ease;
            }
            input[type="text"]:focus, input[type="password"]:focus {
                border-color: #4CAF50;
                outline: none;
                box-shadow: 0 0 10px rgba(76, 175, 80, 0.2);
            }
            .login-btn {
                width: 100%;
                padding: 15px;
                background: linear-gradient(45deg, #4CAF50, #45a049);
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 16px;
                font-weight: bold;
                cursor: pointer;
                transition: all 0.3s ease;
                margin-top: 10px;
            }
            .login-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 20px rgba(76, 175, 80, 0.3);
            }
            .demo-info {
                background: #e8f5e8;
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 25px;
                border-left: 4px solid #4CAF50;
                font-size: 14px;
            }
            .demo-account {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin: 8px 0;
                padding: 8px;
                background: white;
                border-radius: 5px;
            }
            .error-message {
                background: #ffebee;
                color: #c62828;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 20px;
                border-left: 4px solid #f44336;
                font-size: 14px;
            }
            .system-info {
                text-align: center;
                margin-top: 20px;
                font-size: 12px;
                color: #666;
            }
        </style>
    </head>
    <body>
        <div class="login-container">
            <div class="logo">
                <h1>🏥 サロン管理</h1>
                <p>スタッフ欠勤・代替手配システム</p>
            </div>
            
            {% if error_message %}
            <div class="error-message">
                ❌ {{ error_message }}
            </div>
            {% endif %}
            
            <div class="demo-info">
                <strong>📝 デモアカウント</strong>
                <div class="demo-account">
                    <span><strong>スタッフ:</strong> staff001</span>
                    <span><strong>Pass:</strong> pass123</span>
                </div>
                <div class="demo-account">
                    <span><strong>管理者:</strong> admin</span>
                    <span><strong>Pass:</strong> admin123</span>
                </div>
            </div>
            
            <form method="post">
                <div class="form-group">
                    <label for="username">スタッフID</label>
                    <input type="text" 
                           id="username" 
                           name="username" 
                           placeholder="staff001 または admin" 
                           required
                           value="{{ request.form.get('username', '') }}">
                </div>
                
                <div class="form-group">
                    <label for="password">パスワード</label>
                    <input type="password" 
                           id="password" 
                           name="password" 
                           placeholder="パスワードを入力" 
                           required>
                </div>
                
                <button type="submit" class="login-btn">
                    ログイン
                </button>
            </form>
            
            <div class="system-info">
                システム稼働中 | ポート: 5001
            </div>
        </div>
    </body>
    </html>
    """
    
    return render_template_string(login_template, error_message=error_message)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🏥 サロン管理システム - Step 1: ログイン画面")
    print("="*50)
    print("📍 URL: http://localhost:5001/")
    print("🔐 デモアカウント:")
    print("   staff001 / pass123")
    print("   admin / admin123")
    print("✓ 美しいログイン画面")
    print("✓ エラーハンドリング")
    print("✓ 入力バリデーション")
    print("="*50)
    
    app.run(host='0.0.0.0', port=5001, debug=True)
