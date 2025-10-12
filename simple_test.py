from flask import Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "Hello! Flask is working!"

if __name__ == '__main__':
    print("Starting Flask...")
    app.run(host='127.0.0.1', port=5001, debug=False)
