#!/bin/bash
while true; do
    echo "システム起動中..."
    python3 notification_system.py
    echo "システム停止 - 5秒後に再起動..."
    sleep 5
done
