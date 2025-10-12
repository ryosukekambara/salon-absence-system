# practical_salon_system.py - 実用的なサロン管理システム
from flask import Flask, request, jsonify, render_template_string, redirect, session, flash
from datetime import datetime, timedelta
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
        "email": "tanaka@salon.com",
        "role": "スタイリスト"
    },
    "admin": {
        "name": "管理者", 
        "password": "admin123", 
        "skills": ["管理"], 
        "phone": "090-0000-0000",
        "email": "admin@salon.com",
        "role": "管理者"
    }
}

absence_logs = []

@app.route('/')
def dashboard():
    if 'logged_in' not in session:
        return redirect('/login')
    return "<h1>サロン管理システム - ダッシュボード</h1><p>ログイン成功</p><a href='/logout'>ログアウト</a>"

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username in staff_data and staff_data[username]['password'] == password:
            session['logged_in'] = True
            session['user'] = username
            return redirect('/')
    
    return '''
    <form method="post">
        <h2>ログイン</h2>
        <p>ID: <input name="username" placeholder="staff001 or admin"></p>
        <p>パスワード: <input type="password" name="password" placeholder="pass123 or admin123"></p>
        <p><button type="submit">ログイン</button></p>
    </form>
    '''

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    print("サロン管理システム起動")
    print("URL: http://localhost:5001/")
    print("デモアカウント: staff001/pass123 または admin/admin123")
    app.run(host='0.0.0.0', port=5001, debug=True)
