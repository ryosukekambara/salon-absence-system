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
        <title>ダッシュボード - スタッフ管理システム</title>
        <script src="https://unpkg.com/lucide@latest/dist/umd/lucide.js"></script>
        <style>
            body { font-family: 'Hiragino Sans', Arial, sans-serif; margin: 0; padding: 0; background: #f5f3f0; }
            .header { background: linear-gradient(135deg, #8b7355 0%, #6b5b47 100%); color: white; padding: 20px; display: flex; justify-content: space-between; align-items: center; }
            .user-info { display: flex; align-items: center; gap: 15px; }
            .logout-btn { background: #a0522d; padding: 10px 15px; border-radius: 5px; text-decoration: none; color: white; display: flex; align-items: center; gap: 8px; }
            .container { max-width: 1200px; margin: 20px auto; padding: 0 20px; }
            .nav { background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(139, 115, 85, 0.1); border: 1px solid #e8e0d6; }
            .nav a { display: inline-block; margin-right: 15px; padding: 12px 20px; background: #8b7355; color: white; text-decoration: none; border-radius: 8px; display: inline-flex; align-items: center; gap: 8px; }
            .nav a:hover { background: #6b5b47; }
            .dashboard-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
            .card { background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 10px rgba(139, 115, 85, 0.1); border: 1px solid #e8e0d6; }
            .stat-number { font-size: 2.5em; font-weight: bold; color: #8b7355; margin: 10px 0; }
            .quick-action { background: #f8f6f3; padding: 15px; border-radius: 8px; margin: 10px 0; border: 1px solid #e8e0d6; }
            .quick-action a { background: #8b7355; color: white; padding: 8px 15px; text-decoration: none; border-radius: 5px; display: inline-flex; align-items: center; gap: 6px; }
            .alert { padding: 15px; margin: 20px 0; border-radius: 8px; }
            .alert-success { background: #f0f8e8; color: #2e7d1c; border: 1px solid #d4edda; }
            .card-header { display: flex; align-items: center; gap: 10px; margin-bottom: 15px; }
            .card-title { color: #6b5b47; font-weight: 600; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>スタッフ管理システム</h1>
            <div class="user-info">
                <span>{{ user_name }}さん ({{ user_role }})</span>
                <a href="/logout" class="logout-btn">
                    <i data-lucide="log-out"></i>
                    ログアウト
                </a>
            </div>
        </div>
        
        <div class="container">
            {% for message in get_flashed_messages() %}
                <div class="alert alert-success">{{ message }}</div>
            {% endfor %}
            
            <div class="nav">
                <a href="/staff">
                    <i data-lucide="users"></i>
                    スタッフ管理
                </a>
                <a href="/absence">
                    <i data-lucide="file-text"></i>
                    欠勤登録
                </a>
                <a href="/recruitment">
                    <i data-lucide="search"></i>
                    代替募集
                </a>
                <a href="/reports">
                    <i data-lucide="bar-chart-3"></i>
                    レポート
                </a>
            </div>
            
            <div class="dashboard-grid">
                <div class="card">
                    <div class="card-header">
                        <i data-lucide="users" style="color: #8b7355;"></i>
                        <h3 class="card-title">スタッフ状況</h3>
                    </div>
                    <div class="stat-number">{{ staff_count }}</div>
                    <p>登録スタッフ数</p>
                    <div class="quick-action">
                        <a href="/staff">
                            <i data-lucide="eye"></i>
                            スタッフ一覧
                        </a>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-header">
                        <i data-lucide="calendar-x" style="color: #8b7355;"></i>
                        <h3 class="card-title">今日の欠勤</h3>
                    </div>
                    <div class="stat-number">{{ today_absences }}</div>
                    <p>欠勤登録</p>
                    <div class="quick-action">
                        <a href="/absence">
                            <i data-lucide="plus"></i>
                            欠勤登録
                        </a>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-header">
                        <i data-lucide="user-plus" style="color: #8b7355;"></i>
                        <h3 class="card-title">代替募集</h3>
                    </div>
                    <div class="stat-number">{{ active_recruitments }}</div>
                    <p>募集中</p>
                    <div class="quick-action">
                        <a href="/recruitment">
                            <i data-lucide="settings"></i>
                            募集管理
                        </a>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-header">
                        <i data-lucide="activity" style="color: #8b7355;"></i>
                        <h3 class="card-title">システム状態</h3>
                    </div>
                    <div class="stat-number" style="color: #2e7d1c;">
                        <i data-lucide="check-circle"></i>
                    </div>
                    <p>正常稼働中</p>
                    <p><small>ポート: 5001</small></p>
                </div>
            </div>
        </div>

        <script>
            lucide.createIcons();
        </script>
    </body>
    </html>
    """
    
    user_data = staff_data.get(session['user'], {})
    today = datetime.now().strftime('%Y-%m-%d')
    
    return render_template_string(template,
        user_name=user_data.get('name', 'ユーザー'),
        user_role=user_data.get('role', ''),
        staff_count=len(staff_data)-1,
        today_absences=len([a for a in absence_logs if a.get('date') == today]),
        active_recruitments=len(recruitment_logs)
    )

@app.route('/absence', methods=['GET', 'POST'])
def absence_registration():
    if 'logged_in' not in session:
        return redirect('/login')
    
    if request.method == 'POST':
        absence_record = {
            "id": f"abs_{len(absence_logs)+1:03d}",
            "staff_id": session['user'],
            "staff_name": session.get('user_name'),
            "date": request.form['absence_date'],
            "start_time": request.form['start_time'],
            "end_time": request.form['end_time'],
            "reason": request.form['reason'],
            "details": request.form.get('details', ''),
            "notification_method": request.form['notification_method'],
            "created_at": datetime.now().isoformat(),
            "status": "registered"
        }
        
        absence_logs.append(absence_record)
        flash(f"欠勤登録が完了しました。ID: {absence_record['id']}")
        
        recruitment_record = {
            "id": f"rec_{len(recruitment_logs)+1:03d}",
            "absence_id": absence_record["id"],
            "work_date": absence_record["date"],
            "work_time": f"{absence_record['start_time']}-{absence_record['end_time']}",
            "required_skills": staff_data[session['user']]['skills'],
            "status": "active",
            "created_at": datetime.now().isoformat()
        }
        recruitment_logs.append(recruitment_record)
        
        return redirect('/')
    
    template = """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <title>欠勤登録 - スタッフ管理システム</title>
        <script src="https://unpkg.com/lucide@latest/dist/umd/lucide.js"></script>
        <style>
            body { font-family: 'Hiragino Sans', Arial, sans-serif; margin: 0; padding: 0; background: #f5f3f0; }
            .header { background: linear-gradient(135deg, #8b7355 0%, #6b5b47 100%); color: white; padding: 15px 20px; display: flex; align-items: center; gap: 15px; }
            .container { max-width: 800px; margin: 20px auto; padding: 0 20px; }
            .form-container { background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(139, 115, 85, 0.1); border: 1px solid #e8e0d6; }
            .form-group { margin-bottom: 20px; }
            label { display: block; margin-bottom: 8px; font-weight: 600; color: #6b5b47; display: flex; align-items: center; gap: 8px; }
            input, select, textarea { width: 100%; padding: 12px; border: 2px solid #e8e0d6; border-radius: 8px; box-sizing: border-box; font-size: 16px; }
            input:focus, select:focus, textarea:focus { border-color: #8b7355; outline: none; }
            .time-group { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
            .btn { padding: 15px 30px; background: linear-gradient(135deg, #8b7355 0%, #6b5b47 100%); color: white; border: none; border-radius: 8px; font-size: 16px; cursor: pointer; display: inline-flex; align-items: center; gap: 8px; }
            .btn:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(139, 115, 85, 0.3); }
            .nav-back { background: #8b7355; color: white; padding: 10px 15px; text-decoration: none; border-radius: 5px; display: inline-flex; align-items: center; gap: 8px; }
            .info-box { background: linear-gradient(135deg, #f8f6f3 0%, #f0ede8 100%); padding: 20px; border-radius: 8px; margin-bottom: 25px; border: 1px solid #e8e0d6; }
        </style>
    </head>
    <body>
        <div class="header">
            <i data-lucide="file-text"></i>
            <h1>欠勤登録</h1>
        </div>
        
        <div class="container">
            <div style="margin-bottom: 20px;">
                <a href="/" class="nav-back">
                    <i data-lucide="arrow-left"></i>
                    ダッシュボード
                </a>
            </div>
            
            <div class="form-container">
                <div class="info-box">
                    <strong>{{ user_name }}さんの欠勤登録</strong><br>
                    登録後、自動的に代替スタッフの募集が開始されます。
                </div>
                
                <form method="post">
                    <div class="form-group">
                        <label for="absence_date">
                            <i data-lucide="calendar"></i>
                            欠勤日 *
                        </label>
                        <input type="date" id="absence_date" name="absence_date" required min="{{ min_date }}">
                    </div>
                    
                    <div class="time-group">
                        <div class="form-group">
                            <label for="start_time">
                                <i data-lucide="clock"></i>
                                開始時間 *
                            </label>
                            <input type="time" id="start_time" name="start_time" required>
                        </div>
                        
                        <div class="form-group">
                            <label for="end_time">
                                <i data-lucide="clock"></i>
                                終了時間 *
                            </label>
                            <input type="time" id="end_time" name="end_time" required>
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label for="reason">
                            <i data-lucide="alert-circle"></i>
                            欠勤理由 *
                        </label>
                        <select id="reason" name="reason" required>
                            <option value="">選択してください</option>
                            <option value="体調不良">体調不良</option>
                            <option value="発熱">発熱</option>
                            <option value="家族の事情">家族の事情</option>
                            <option value="急用">急用</option>
                            <option value="交通機関の遅延">交通機関の遅延</option>
                            <option value="その他">その他</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label for="details">
                            <i data-lucide="message-square"></i>
                            詳細・備考
                        </label>
                        <textarea id="details" name="details" rows="3" placeholder="必要に応じて詳細をご記入ください"></textarea>
                    </div>
                    
                    <div class="form-group">
                        <label for="notification_method">
                            <i data-lucide="bell"></i>
                            通知方法 *
                        </label>
                        <select id="notification_method" name="notification_method" required>
                            <option value="line">LINE通知</option>
                            <option value="sms">SMS通知</option>
                            <option value="email">メール通知</option>
                        </select>
                    </div>
                    
                    <button type="submit" class="btn">
                        <i data-lucide="check"></i>
                        欠勤を登録
                    </button>
                </form>
            </div>
        </div>

        <script>
            lucide.createIcons();
        </script>
    </body>
    </html>
    """
    
    min_date = datetime.now().strftime('%Y-%m-%d')
    user_data = staff_data.get(session['user'], {})
    
    return render_template_string(template, 
        min_date=min_date,
        user_name=user_data.get('name', 'ユーザー')
    )

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
        <title>ログイン - スタッフ管理システム</title>
        <style>
            body { 
                font-family: 'Hiragino Sans', Arial, sans-serif; 
                background: #f5f3f0; 
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
                border-radius: 15px; 
                box-shadow: 0 10px 30px rgba(139, 115, 85, 0.2); 
                overflow: hidden;
                width: 100%;
                max-width: 400px;
            }
            .header-section {
                background: linear-gradient(135deg, #8b7355 0%, #6b5b47 100%);
                color: white;
                padding: 40px 30px;
                text-align: center;
            }
            .header-section h1 {
                margin: 0;
                font-size: 1.8em;
                font-weight: 600;
            }
            .header-section p {
                margin: 8px 0 0 0;
                opacity: 0.9;
                font-size: 14px;
            }
            .form-section {
                padding: 40px 30px;
            }
            .tab-nav {
                display: flex;
                border-bottom: 1px solid #e8e0d6;
                margin-bottom: 30px;
            }
            .tab {
                flex: 1;
                padding: 15px 0;
                text-align: center;
                color: #8b7355;
                font-weight: 600;
                border-bottom: 3px solid #8b7355;
                cursor: pointer;
            }
            .tab:not(.active) {
                color: #ccc;
                border-bottom-color: transparent;
            }
            {% if error_message %}
            .error-message { 
                background: #fff5f5; 
                color: #c53030; 
                padding: 12px; 
                border-radius: 8px; 
                margin-bottom: 20px; 
                border: 1px solid #fed7d7;
                font-size: 14px;
            }
            {% endif %}
            .demo-info { 
                background: #f8f6f3; 
                padding: 15px; 
                border-radius: 8px; 
                margin-bottom: 25px; 
                font-size: 13px;
                border: 1px solid #e8e0d6;
            }
            .form-group {
                margin-bottom: 20px;
            }
            .form-group label {
                display: block;
                margin-bottom: 8px;
                font-weight: 600;
                color: #6b5b47;
                font-size: 14px;
            }
            input { 
                width: 100%; 
                padding: 15px; 
                border: 2px solid #e8e0d6; 
                border-radius: 8px; 
                box-sizing: border-box; 
                font-size: 16px;
                transition: all 0.3s ease;
            }
            input:focus { 
                border-color: #8b7355; 
                outline: none; 
                box-shadow: 0 0 0 3px rgba(139, 115, 85, 0.1);
            }
            .login-btn { 
                width: 100%; 
                padding: 15px; 
                background: linear-gradient(135deg, #8b7355 0%, #6b5b47 100%); 
                color: white; 
                border: none; 
                border-radius: 8px; 
                cursor: pointer; 
                font-size: 16px;
                font-weight: 600;
                transition: all 0.3s ease;
            }
            .login-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 20px rgba(139, 115, 85, 0.3);
            }
            .forgot-links {
                display: flex;
                justify-content: space-between;
                margin-top: 20px;
            }
            .forgot-link {
                color: #8b7355;
                text-decoration: none;
                font-size: 13px;
                padding: 8px 15px;
                background: #f8f6f3;
                border-radius: 5px;
                border: 1px solid #e8e0d6;
            }
        </style>
    </head>
    <body>
        <div class="login-container">
            <div class="header-section">
                <h1>スタッフ管理システム</h1>
                <p>安全で効率的なスタッフ管理</p>
            </div>
            
            <div class="form-section">
                <div class="tab-nav">
                    <div class="tab active">ログイン</div>
                </div>
                
                {% if error_message %}
                <div class="error-message">{{ error_message }}</div>
                {% endif %}
                
                <div class="demo-info">
                    <strong>デモアカウント:</strong><br>
                    staff001 / pass123<br>
                    staff002 / pass456<br>
                    admin / admin123
                </div>
                
                <form method="post">
                    <div class="form-group">
                        <label>ID</label>
                        <input type="text" name="username" placeholder="staff001 または admin" required>
                    </div>
                    
                    <div class="form-group">
                        <label>パスワード</label>
                        <input type="password" name="password" placeholder="パスワードを入力" required>
                    </div>
                    
                    <button type="submit" class="login-btn">ログイン</button>
                </form>
                
                <div class="forgot-links">
                    <a href="#" class="forgot-link">IDを忘れた</a>
                    <a href="#" class="forgot-link">パスワードを忘れた</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return render_template_string(login_template, error_message=error_message)

# その他のページ
@app.route('/staff')
def staff_management():
    if 'logged_in' not in session:
        return redirect('/login')
    return f"<h1>スタッフ管理</h1><p>Step 4で実装予定</p><a href='/'>← ダッシュボード</a><br><br>現在の登録数: {len(absence_logs)}件"

@app.route('/recruitment')
def recruitment_management():
    if 'logged_in' not in session:
        return redirect('/login')
    
    active_recruitments = [r for r in recruitment_logs if r['status'] == 'active']
    recruitment_list = "<br>".join([f"ID: {r['id']} - 日付: {r['work_date']} - 時間: {r['work_time']}" for r in active_recruitments])
    
    return f"<h1>代替募集管理</h1><p>自動生成された募集:</p><p>{recruitment_list or '募集なし'}</p><a href='/'>← ダッシュボード</a>"

@app.route('/reports')
def reports():
    if 'logged_in' not in session:
        return redirect('/login')
    return f"<h1>レポート</h1><p>欠勤登録数: {len(absence_logs)}件</p><p>代替募集数: {len(recruitment_logs)}件</p><a href='/'>← ダッシュボード</a>"

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    print("\n" + "="*50)
    print("Step 3: Lucideアイコン + 茶色テーマ")
    print("="*50)
    print("URL: http://localhost:5001/")
    print("変更点:")
    print("- 全ての絵文字をLucideアイコンに置換")
    print("- 茶色系カラーテーマに統一")
    print("- ログイン画面を参考画像と同様にデザイン")
    print("="*50)
    
    app.run(host='0.0.0.0', port=5001, debug=True)
