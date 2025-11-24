#!/usr/bin/env python3
import asyncio
import subprocess
import json
from datetime import datetime, timedelta
import os
import tempfile

async def main():
    print(f"[{datetime.now()}] スクレイピング開始")
    
    # 3日後と7日後の日付
    date_3days = (datetime.now() + timedelta(days=3)).strftime("%Y%m%d")
    date_7days = (datetime.now() + timedelta(days=7)).strftime("%Y%m%d")
    
    print(f"対象日付: 3日後={date_3days}, 7日後={date_7days}")
    
    # スクレイピング実行（既存のスクリプト使用）
    result_3 = subprocess.run([
        "python3", "scrape_3days_mac.py"
    ], capture_output=True, text=True)
    print(f"3日後スクレイピング結果: {result_3.stdout}")
    if result_3.stderr:
        print(f"3日後エラー: {result_3.stderr}")
    
    result_7 = subprocess.run([
        "python3", "scrape_7days_mac.py"
    ], capture_output=True, text=True)
    print(f"7日後スクレイピング結果: {result_7.stdout}")
    if result_7.stderr:
        print(f"7日後エラー: {result_7.stderr}")
    
    # SSH鍵を環境変数から取得して一時ファイルに書き込む
    ssh_key = os.environ.get("VPS_SSH_PRIVATE_KEY")
    if not ssh_key:
        print("エラー: VPS_SSH_PRIVATE_KEY が設定されていません")
        return {"success": False, "message": "SSH鍵が未設定"}
    
    # 一時ファイルにSSH鍵を保存
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='_key') as f:
        f.write(ssh_key)
        key_path = f.name
    
    # 鍵ファイルのパーミッションを設定
    os.chmod(key_path, 0o600)
    
    # VPSに転送
    vps_ip = "153.120.1.43"
    
    # known_hostsチェックをスキップするオプション
    scp_options = [
        "scp",
        "-i", key_path,
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null"
    ]
    
    # 3日後のファイル転送
    result_scp_3 = subprocess.run(
        scp_options + [
            "scrape_result_3days.json",
            f"ubuntu@{vps_ip}:~/"
        ],
        capture_output=True, text=True
    )
    print(f"SCP 3days: {result_scp_3.returncode}, {result_scp_3.stdout}, {result_scp_3.stderr}")
    
    # 7日後のファイル転送
    result_scp_7 = subprocess.run(
        scp_options + [
            "scrape_result_7days.json",
            f"ubuntu@{vps_ip}:~/"
        ],
        capture_output=True, text=True
    )
    print(f"SCP 7days: {result_scp_7.returncode}, {result_scp_7.stdout}, {result_scp_7.stderr}")
    
    # 一時ファイルを削除
    os.unlink(key_path)
    
    print(f"[{datetime.now()}] 完了")
    return {"success": True, "message": "スクレイピング完了"}

if __name__ == "__main__":
    result = asyncio.run(main())
    print(json.dumps(result, ensure_ascii=False))
