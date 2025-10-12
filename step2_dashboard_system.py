from flask import Flask, request, jsonify, render_template_string, redirect, session, flash
from datetime import datetime, timedelta
import json

app = Flask(__name__)
app.secret_key = 'salon-management-secret-2025'

# データストレージ
staff_data = {
    "staff001": {"name": "田中美咲", "password": "pass123", "skills": ["カット", "カラー"], "phone": "090-1111-1111", "role": "スタイリスト"},
    "staff002": {"name": "佐藤花子", "password": "pass456", "skills": ["パーマ", "トリートメント"], "phone": "090-2222-2222", "role": "スタイリスト"},
    "admin": {"name": "管理者", "password": "admin123", "skills": ["管理"], "phone": "090-0000-0000", "role": "管理者"}
}

absence_logs = []
recruitment_logs = []

@app.route('/')
def dashboard():
    if 'logged_in' not in session:
        return redirect('/login')
    
    template = """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <title>ダッシュボード - サロン管理システム</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 0; background: #f5f7fa; }
            .header { background: linear-gradient(45deg, #4CAF50, #45a049); color: white; padding: 20px; display: flex; justify-content: space-between; align-items: center; }
            .user-info { display: flex; align-items: center; gap: 15px; }
            .logout-btn { background: #f44336; padding: 10px 15px; border-radius: 5px; text-decoration: none; color: white; }
            .container { max-width: 1200px; margin: 20px auto; padding: 0 20px; }
            .nav { background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .nav a { display: inline-block; margin-right: 15px; padding: 12px 20px; background: #2196F3; color: white; text-decoration: none; border-radius: 8px; }
            .nav a:hover { background: #1976D2; }
            .dashboard-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
            .card { background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .stat-number { font-size: 2.5em; font-weight: bold; color: #4CAF50; margin: 10px 0; }
            .quick-action { background: #e3f2fd; padding: 15px; border-radius: 8px; margin: 10px 0; }
            .quick-action a { background: #2196F3; color: white; padding: 8px 15px; text-decoration: none; border-radius: 5px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>サロン管理システム</h1>
            <div class="user-info">
                <span>{{ user_name }}さん ({{ user_role }})</span>
                <a href="/logout" class="logout-btn">ログアウト</a>
            </div>
        </div>
        
        <div class="container">
            <div class="nav">
                <a href="/staff">👥 スタッフ管理</a>
                <a href="/absence">📝 欠勤登録</a>
                <a href="/recruitment">🔍 代替募集</a>
                <a href="/reports">📊 レポート</a>
            </div>
            
            <div class="dashboard-grid">
                <div class="card">
                    <h3>📊 スタッフ状況</h3>
                    <div class="stat-number">{{ staff_count }}</div>
                    <p>登録スタッフ数</p>
                    <div class="quick-action">
                        <a href="/staff">スタッフ一覧</a>
                    </div>
                </div>
                
                <div class="card">
                    <h3>📅 今日の欠勤</h3>
                    <div class="stat-number">{{ today_absences }}</div>
                    <p>欠勤登録</p>
                    <div class="quick-action">
                        <a href="/absence">欠勤登録</a>
                    </div>
                </div>
                
                <div class="card">
                    <h3>🔍 代替募集</h3>
                    <div class="stat-number">{{ active_recruitments }}</div>
                    <p>募集中</p>
                    <div class="quick-action">
                        <a href="/recruitment">募集管理</a>
                    </div>
                </div>
                
                <div class="card">
                    <h3>📱 システム状態</h3>
                    <div class="stat-number" style="color: #4CAF50;">✓</div>
                    <p>正常稼働中</p>
                    <p><small>ポート: 5001</small></p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    user_data = staff_data.get(session['user'], {})
    today = datetime.now().strftime('%Y-%m-%d')
    
    return render_template_string(template,
        user_name=user_data.get('name', 'ユーザー'),
        user_role=user_data.get('role', ''),
        staff_count=len(staff_data)-1,  # 管理者除く
        today_absences=len([a for a in absence_logs if a.get('date') == today]),
        active_recruitments=len(recruitment_logs)
    )

# Step 1のログイン機能をそのまま使用
@app.route('/login', methods=['GET', 'POST'])
def login():
    error_message = ""
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
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
        <title>ログイン - サロン管理システム</title>
        <style>
            body { font-family: Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
            .login-container { background: white; padding: 40px; border-radius: 15px; box-shadow: 0 15px 35px rgba(0,0,0,0.2); max-width: 400px; }
            .logo { text-align: center; margin-bottom: 30px; }
            .logo h1 { color: #4CAF50; margin: 0; }
            input { width: 100%; padding: 12px; border: 2px solid #e0e0e0; border-radius: 8px; margin: 10px 0; box-sizing: border-box; }
            input:focus { border-color: #4CAF50; outline: none; }
            .login-btn { width: 100%; padding: 15px; background: #4CAF50; color: white; border: none; border-radius: 8px; cursor: pointer; }
            .error-message { background: #ffebee; color: #c62828; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
            .demo-info { background: #e8f5e8; padding: 15px; border-radius: 8px; margin-bottom: 20px; font-size: 14px; }
        </style>
    </head>
    <body>
        <div class="login-container">
            <div class="logo">
                <h1>🏥 サロン管理</h1>
            </div>
            
            {% if error_message %}
            <div class="error-message">{{ error_message }}</div>
            {% endif %}
            
            <div class="demo-info">
                <strong>デモアカウント:</strong><br>
                staff001 / pass123<br>
                admin / admin123
            </div>
            
            <form method="post">
                <input type="text" name="username" placeholder="スタッフID" required>
                <input type="password" name="password" placeholder="パスワード" required>
                <button type="submit" class="login-btn">ログイン</button>
            </form>
        </div>
    </body>
    </html>
    """
    
    return render_template_string(login_template, error_message=error_message)

# 各機能ページのプレースホルダー
@app.route('/staff')
def staff_management():
    if 'logged_in' not in session:
        return redirect('/login')
    return "<h1>スタッフ管理</h1><p>Step 3で実装予定</p><a href='/'>← ダッシュボード</a>"

@app.route('/absence')
def absence_form():
    if 'logged_in' not in session:
        return redirect('/login')
    return "<h1>欠勤登録</h1><p>Step 3で実装予定</p><a href='/'>← ダッシュボード</a>"

@app.route('/recruitment')
def recruitment_management():
    if 'logged_in' not in session:
        return redirect('/login')
    return "<h1>代替募集管理</h1><p>Step 4で実装予定</p><a href='/'>← ダッシュボード</a>"

@app.route('/reports')
def reports():
    if 'logged_in' not in session:
        return redirect('/login')
    return "<h1>レポート</h1><p>Step 5で実装予定</p><a href='/'>← ダッシュボード</a>"

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🏥 Step 2: 基本管理画面システム")
    print("="*50)
    print("📍 URL: http://localhost:5001/")
    print("✓ 美しいダッシュボード")
    print("✓ ナビゲーション機能")
    print("✓ 統計表示")
    print("✓ 各機能への導線")
    print("="*50)
    
    app.run(host='0.0.0.0', port=5001, debug=True)
