#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SALON BOARD アクセステスト (詳細版)
より本物のブラウザに近い設定でテスト
"""

import requests
from bs4 import BeautifulSoup

LOGIN_URL = "https://salonboard.com/login/"

def test_with_detailed_headers():
    """より詳細なヘッダーでアクセステスト"""

    print("=" * 60)
    print("詳細ヘッダーでのアクセステスト")
    print("=" * 60)

    session = requests.Session()

    # より本物のブラウザに近いヘッダー
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    })

    print("\n[テスト1] 詳細ヘッダーでアクセス...")
    try:
        response = session.get(LOGIN_URL, timeout=10)
        print(f"ステータスコード: {response.status_code}")
        print(f"レスポンスサイズ: {len(response.text)} bytes")
        print(f"Content-Type: {response.headers.get('Content-Type', 'N/A')}")

        if response.status_code == 403:
            print("\n❌ 403 Forbidden - Bot検知されています")
            print("\nレスポンスヘッダー:")
            for key, value in response.headers.items():
                print(f"  {key}: {value}")

            print("\nレスポンス内容:")
            print(response.text[:1000])

        elif response.status_code == 200:
            print("\n✅ アクセス成功")
            soup = BeautifulSoup(response.text, 'html.parser')
            title = soup.find('title')
            if title:
                print(f"ページタイトル: {title.text}")

            # ログインフォームの確認
            forms = soup.find_all('form')
            print(f"フォーム数: {len(forms)}")

        else:
            print(f"\n⚠️  予期しないステータスコード: {response.status_code}")

    except Exception as e:
        print(f"❌ エラー: {e}")

    print("\n" + "=" * 60)
    print("結論:")
    print("=" * 60)

    if response.status_code == 403:
        print("✅ 事実確認完了:")
        print("   - SALON BOARDはBot検知システムを使用")
        print("   - requests + beautifulsoup4 では403エラー")
        print("   - Playwright（実ブラウザ）が必須")
        print("\n推奨:")
        print("   1. Playwright を使う（Render有料プラン必要）")
        print("   2. または別のホスティングサービスを検討")
    elif response.status_code == 200:
        print("✅ requests + beautifulsoup4 で実装可能")
        print("   Playwrightは不要")
    else:
        print("⚠️  追加調査が必要")

if __name__ == "__main__":
    test_with_detailed_headers()
