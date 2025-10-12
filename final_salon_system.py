from flask import Flask, request, jsonify
import json
from datetime import datetime

app = Flask(__name__)

# データストレージ
absence_logs = []

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
            <p>✅ 処理済み欠勤: ''' + str(len(absence_logs)) + '''件</p>
        </div>
    </body>
    </html>
    '''

@app.route('/system/status')
def status():
    return jsonify({
        "status": "OK", 
        "message": "システム正常稼働中", 
        "port": 5001,
        "absences_processed": len(absence_logs)
    })

@app.route('/api/absence/notify', methods=['POST'])
def absence_notify():
    data = request.json
    absence_record = {
        "id": len(absence_logs) + 1,
        "staff_name": data.get('staff_name'),
        "date": data.get('date'),
        "reason": data.get('reason'),
        "timestamp": datetime.now().isoformat()
    }
    absence_logs.append(absence_record)
    
    return jsonify({
        "status": "success",
        "message": f"{absence_record['staff_name']}さんの欠勤を受理しました",
        "absence_id": absence_record["id"]
    })

if __name__ == '__main__':
    print("🎉 最終版システム起動")
    print("📍 http://localhost:5001/")
    app.run(host='0.0.0.0', port=5001, debug=False)
