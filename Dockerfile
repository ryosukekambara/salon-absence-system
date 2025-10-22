# Playwright公式のPythonイメージ（ブラウザとシステム依存関係が含まれる）
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# 作業ディレクトリを設定
WORKDIR /app

# Python依存関係をコピーしてインストール
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# アプリケーションのソースコードをコピー
COPY . .

# Renderが使用するポート（環境変数から取得）
ENV PORT=10000

# Gunicornでアプリケーションを起動
CMD gunicorn --bind 0.0.0.0:$PORT auth_notification_system:app
