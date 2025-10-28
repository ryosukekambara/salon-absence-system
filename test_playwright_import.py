#!/usr/bin/env python3
import sys
import time

print("[TEST] 開始", flush=True)
start = time.time()

try:
    print("[TEST] playwright インポート中...", flush=True)
    from playwright.sync_api import sync_playwright
    print(f"[TEST] playwright インポート完了: {time.time() - start:.2f}秒", flush=True)
    
    print("[TEST] playwright 起動中...", flush=True)
    with sync_playwright() as p:
        print(f"[TEST] playwright 起動完了: {time.time() - start:.2f}秒", flush=True)
        
        print("[TEST] chromium 起動中...", flush=True)
        browser = p.chromium.launch(headless=True)
        print(f"[TEST] chromium 起動完了: {time.time() - start:.2f}秒", flush=True)
        
        browser.close()
        print(f"[TEST] 完了: {time.time() - start:.2f}秒", flush=True)
        
except Exception as e:
    print(f"[TEST] エラー: {type(e).__name__}: {str(e)}", flush=True)
    import traceback
    traceback.print_exc()
