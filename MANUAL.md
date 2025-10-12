# スタッフ管理システム 運用マニュアル

## システム起動方法
cd ~/salon-absence-system
python3 auth_notification_system.py

アクセス: http://localhost:5001/

## ログイン情報
管理者: admin / admin123
神原: kambara / kambara123
Saori: saori / saori123

## 欠勤申請の流れ
1. スタッフがログイン→欠勤申請
2. 他のスタッフにLINE通知
3. 代替スタッフが「出勤できます」と返信
4. 顧客に自動通知

## トラブルシューティング
サーバーが起動しない場合:
lsof -ti:5001 | xargs kill -9
python3 auth_notification_system.py

完成日: 2025-10-11

---

## 👥 顧客の手動登録方法

### ステップ1: customer_mapping.jsonを開く
```bash
cd ~/salon-absence-system
nano customer_mapping.json
{
  "山田太郎": {
    "user_id": "LINE User ID（Uから始まる33文字）",
    "registered_at": "2025-10-11T21:00:00"
  },
  "佐藤花子": {
    "user_id": "U1234567890abcdef12345678901234567",
    "registered_at": "2025-10-11T21:00:00"
  }
}
**このコマンドを実行してください！😊**

### LINE User IDの取得方法
1. LINE Official Account Manager にログイン
2. チャット → 該当顧客を選択
3. User ID をコピー（Uから始まる33文字）

保存: Control + O → Enter → Control + X

---

## 🔔 自動リマインド機能（将来実装予定）

- 予約7日前: 予約確認リマインド
- 予約3日前: 最終確認リマインド
- 定期メンテナンス案内
- キャンペーン通知

実装時期: 顧客データが20人以上登録後
