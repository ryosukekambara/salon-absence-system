import socket
from flask import Flask, jsonify

print("🔍 デバッグアプリ開始...")

def check_port(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            print(f"✅ ポート{port}は利用可能です")
            return True
        except socket.error as e:
            print(f"❌ ポート{port}エラー: {e}")
            return False

if not check_port('0.0.0.0', 5001):
    print("⚠️  ポート5001が使用中です。別のポートを試します...")
    PORT = 5002 if check_port('0.0.0.0', 5002) else 8000
else:
    PORT = 5001

app = Flask(__name__)

@app.route('/')
def home():
    print(f"📥 ホームページアクセス受信")
    return jsonify({"message": "🎉 デバッグアプリ動作中！", "status": "OK", "port": PORT})

@app.route('/test')
def test():
    print(f"📥 テストページアクセス受信")
    return "TEST OK - デバッグアプリ正常動作"

if __name__ == '__main__':
    print(f"🚀 デバッグアプリをポート{PORT}で起動...")
    print(f"📍 URL: http://localhost:{PORT}")
    print(f"📍 テスト: http://localhost:{PORT}/test")
    
    try:
        app.run(host='127.0.0.1', port=PORT, debug=True, use_reloader=False)
    except Exception as e:
        print(f"❌ 起動失敗: {e}")
        app.run(host='127.0.0.1', port=8000, debug=True, use_reloader=False)
