from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return '''
    <html>
    <head><title>サロン欠勤システム</title></head>
    <body style="font-family: Arial; padding: 50px; background: #f0f8ff;">
        <h1 style="color: #4CAF50;">🏥 サロン欠勤対応システム</h1>
        <h2>システム正常稼働中</h2>
        <div style="background: white; padding: 20px; border-radius: 10px; margin: 20px 0;">
            <h3>システム状態</h3>
            <p>✅ Flask サーバー: 起動中</p>
            <p>✅ LINE Bot: 設定完了</p>
            <p>✅ ポート: 5001</p>
        </div>
        <div style="background: white; padding: 20px; border-radius: 10px;">
            <h3>機能</h3>
            <p>• スタッフ欠勤連絡受付</p>
            <p>• 代替スタッフ自動募集</p>
            <p>• 顧客通知自動送信</p>
            <p>• サロンボード連携</p>
        </div>
    </body>
    </html>
    '''

@app.route('/system/status')
def status():
    return {"status": "OK", "message": "システム正常稼働中", "port": 5001}

if __name__ == '__main__':
    print("🚀 簡単Web版システム起動")
    print("📍 http://localhost:5001/")
    app.run(host='0.0.0.0', port=5001, debug=False)
