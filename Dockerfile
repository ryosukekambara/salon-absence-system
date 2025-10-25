# Playwright公式のPythonイメージ
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    playwright install chromium firefox

COPY . .

ENV PORT=10000

CMD gunicorn --bind 0.0.0.0:$PORT auth_notification_system:app
