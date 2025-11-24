import sys

with open('auth_notification_system.py', 'r', encoding='utf-8') as f:
    content = f.read()

# timeout=60を timeout=300に変更
content = content.replace('timeout=60,', 'timeout=300,')

with open('auth_notification_system.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("修正完了: timeout=60 → timeout=300")
