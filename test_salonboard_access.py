#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SALON BOARD アクセステスト
requests + beautifulsoup4 で予約情報が取得できるか確認
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime

# SALON BOARD ログイン情報
LOGIN_URL = "https://salonboard.com/login/"
LOGIN_ID = "CD18317"
LOGIN_PASSWORD = "Ne8T2Hhi!"
SCHEDULE_URL = "https://salonboard.com/KLP/schedule/salonSchedule/"

def test_salonboard_access():
    """SALON BOARDにアクセスして情報取得をテスト"""

    print("=" * 60)
    print("SALON BOARD アクセステスト開始")
    print("=" * 60)

    # セッション作成（Cookieを維持）
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })

    # ステップ1: ログインページにアクセス
    print("\n[ステップ1] ログインページにアクセス中...")
    try:
        response = session.get(LOGIN_URL, timeout=10)
        print(f"✅ ステータスコード: {response.status_code}")
        print(f"✅ URL: {response.url}")

        # HTMLを解析してログインフォームを探す
        soup = BeautifulSoup(response.text, 'html.parser')
        login_form = soup.find('form')

        if login_form:
            print("✅ ログインフォームを発見")

            # フォームの入力フィールドを確認
            inputs = login_form.find_all('input')
            print(f"   入力フィールド数: {len(inputs)}")
            for inp in inputs:
                name = inp.get('name', '')
                input_type = inp.get('type', '')
                if name:
                    print(f"   - {name} (type={input_type})")
        else:
            print("⚠️  ログインフォームが見つかりません")

    except Exception as e:
        print(f"❌ エラー: {e}")
        return False

    # ステップ2: ログイン実行
    print("\n[ステップ2] ログイン実行中...")
    try:
        # ログインデータを準備
        login_data = {
            'login_id': LOGIN_ID,
            'password': LOGIN_PASSWORD,
        }

        # CSRFトークンなどがあれば追加
        csrf_token = soup.find('input', {'name': 'csrf_token'})
        if csrf_token:
            login_data['csrf_token'] = csrf_token.get('value', '')
            print("   CSRFトークンを追加")

        # ログイン実行
        response = session.post(LOGIN_URL, data=login_data, timeout=10)
        print(f"✅ ステータスコード: {response.status_code}")
        print(f"✅ リダイレクト後URL: {response.url}")

        # ログイン成功の判定
        if 'login' in response.url.lower():
            print("❌ ログイン失敗（ログインページにリダイレクト）")
            print("\n--- ページ内容の一部 ---")
            print(response.text[:500])
            return False
        else:
            print("✅ ログイン成功の可能性が高い")

    except Exception as e:
        print(f"❌ エラー: {e}")
        return False

    # ステップ3: スケジュール画面にアクセス
    print("\n[ステップ3] スケジュール画面にアクセス中...")
    try:
        # 今日の日付でアクセス
        today = datetime.now().strftime('%Y-%m-%d')
        schedule_url_with_date = f"{SCHEDULE_URL}?date={today}"

        response = session.get(schedule_url_with_date, timeout=10)
        print(f"✅ ステータスコード: {response.status_code}")
        print(f"✅ URL: {response.url}")

        # HTMLを解析
        soup = BeautifulSoup(response.text, 'html.parser')

        # ページタイトルを確認
        title = soup.find('title')
        if title:
            print(f"✅ ページタイトル: {title.text.strip()}")

        # 予約情報らしき要素を探す
        print("\n[予約情報の検索]")

        # パターン1: クラス名で検索
        schedule_elements = soup.find_all(class_=lambda x: x and 'schedule' in x.lower())
        print(f"   'schedule' を含むクラス: {len(schedule_elements)}個")

        # パターン2: 顧客名らしき要素
        customer_elements = soup.find_all(class_=lambda x: x and 'customer' in x.lower())
        print(f"   'customer' を含むクラス: {len(customer_elements)}個")

        # パターン3: 予約らしき要素
        reservation_elements = soup.find_all(class_=lambda x: x and 'reservation' in x.lower())
        print(f"   'reservation' を含むクラス: {len(reservation_elements)}個")

        # パターン4: tableタグ
        tables = soup.find_all('table')
        print(f"   テーブル要素: {len(tables)}個")

        # JavaScript の有無を確認
        scripts = soup.find_all('script')
        print(f"\n[JavaScript解析]")
        print(f"   <script>タグ: {len(scripts)}個")

        # 動的生成を示唆するキーワード
        dynamic_keywords = ['React', 'Vue', 'Angular', 'ajax', 'fetch', 'XMLHttpRequest']
        page_text = response.text.lower()
        found_keywords = [kw for kw in dynamic_keywords if kw.lower() in page_text]

        if found_keywords:
            print(f"   ⚠️  動的生成の可能性: {', '.join(found_keywords)}")
        else:
            print(f"   ✅ サーバーサイドレンダリングの可能性が高い")

        # HTMLの一部を保存（確認用）
        print("\n[HTML保存]")
        with open('/home/user/salon-absence-system/salonboard_test_output.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print("   ✅ salonboard_test_output.html に保存しました")

        # 結果サマリー
        print("\n" + "=" * 60)
        print("テスト結果サマリー")
        print("=" * 60)

        if len(schedule_elements) > 0 or len(tables) > 0:
            print("✅ 予約情報らしき要素が見つかりました")
            print("→ requests + beautifulsoup4 で取得できる可能性が高い")
            print("→ Playwright は不要かもしれません")
            return True
        else:
            print("⚠️  予約情報らしき要素が見つかりません")
            print("→ JavaScript で動的生成されている可能性")
            print("→ Playwright が必要かもしれません")
            return False

    except Exception as e:
        print(f"❌ エラー: {e}")
        return False

if __name__ == "__main__":
    result = test_salonboard_access()

    print("\n" + "=" * 60)
    if result:
        print("結論: requests + beautifulsoup4 で実装可能")
    else:
        print("結論: Playwright が必要な可能性が高い")
    print("=" * 60)
