try:
    from flask import Flask, jsonify
    print("✅ Flaskインポート成功")
except ImportError as e:
    print("❌ Flaskインポートエラー:", e)
    print("解決方法: pip install flask")
    exit(1)

app = Flask(__name__)

@app.route('/')
def home():
    return {"message": "🎉 システム動作中！", "status": "OK"}

@app.route('/system/status')  
def status():
    return jsonify({
        "system": "ONLINE", 
        "port": 5001,
        "message": "正常稼働中"
    })

if __name__ == '__main__':
    try:
        print("\n🚀 最小テストアプリ起動開始...")
        print("📍 URL: http://localhost:5001")
        print("📍 状態確認: http://localhost:5001/system/status")
        print("⭐ 起動完了後は Ctrl+C で終了\n")
        
        app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False)
    except Exception as e:
        print(f"❌ 起動エラー: {e}")
