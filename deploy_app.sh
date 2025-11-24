
#!/bin/bash

set -e

echo "================================"

echo "アプリケーションデプロイ開始"

echo "================================"

GREEN='\033[0;32m'

YELLOW='\033[1;33m'

RED='\033[0;31m'

NC='\033[0m'

APP_DIR="/opt/salon-app"

cd $APP_DIR

echo -e "${YELLOW}[1/6] GitHubからクローン中...${NC}"

if [ -d "salon-absence-system" ]; then

    echo "既存ディレクトリを削除..."

    rm -rf salon-absence-system

fi

git clone https://github.com/ryosukekambara/salon-absence-system.git

cd salon-absence-system

echo -e "${GREEN}✓ クローン完了${NC}"

echo -e "${YELLOW}[2/6] 環境変数ファイル作成中...${NC}"

cat > .env << 'ENV_END'

SALONBOARD_LOGIN_ID=your_salonboard_id

SALONBOARD_LOGIN_PASSWORD=your_salonboard_password

LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token

LINE_CHANNEL_SECRET=your_line_channel_secret

LINE_CHANNEL_ACCESS_TOKEN_STAFF=your_staff_line_token

ADMIN_USERS=kambara:kambara123

FLASK_ENV=production

SECRET_KEY=$(openssl rand -hex 32)

PORT=5000

ENV_END

echo -e "${GREEN}✓ .envファイル作成完了${NC}"

echo ""

echo -e "${YELLOW}[3/6] 環境変数編集を開始します...${NC}"

echo "以下の値を設定してください："

echo ""

read -p "サロンボードID: " SALONBOARD_ID

read -p "サロンボードパスワード: " SALONBOARD_PASS

read -p "LINE Channel Access Token (顧客用): " LINE_TOKEN

read -p "LINE Channel Secret: " LINE_SECRET

read -p "LINE Channel Access Token (スタッフ用): " LINE_STAFF_TOKEN

sed -i "s/your_salonboard_id/$SALONBOARD_ID/" .env

sed -i "s/your_salonboard_password/$SALONBOARD_PASS/" .env

sed -i "s/your_line_channel_access_token/$LINE_TOKEN/" .env

sed -i "s/your_line_channel_secret/$LINE_SECRET/" .env

sed -i "s/your_staff_line_token/$LINE_STAFF_TOKEN/" .env

echo -e "${GREEN}✓ 環境変数設定完了${NC}"

echo -e "${YELLOW}[4/6] Dockerイメージビルド中（3-5分）...${NC}"

docker build -t salon-absence-system:latest .

echo -e "${GREEN}✓ ビルド完了${NC}"

echo -e "${YELLOW}[5/6] 既存コンテナ停止中...${NC}"

docker stop salon-app 2>/dev/null || true

docker rm salon-app 2>/dev/null || true

echo -e "${GREEN}✓ クリーンアップ完了${NC}"

echo -e "${YELLOW}[6/6] コンテナ起動中...${NC}"

docker run -d \

    --name salon-app \

    --restart unless-stopped \

    -p 5000:5000 \

    --env-file .env \

    -v $(pwd)/customer_mapping.json:/app/customer_mapping.json \

    -v $(pwd)/absence_log.json:/app/absence_log.json \

    -v $(pwd)/messages.json:/app/messages.json \

    salon-absence-system:latest

sleep 5

echo -e "${GREEN}✓ コンテナ起動完了${NC}"

if curl -s http://localhost:5000/ > /dev/null; then

    echo -e "${GREEN}✓ アプリケーション起動成功！${NC}"

else

    echo -e "${RED}❌ アプリケーション起動失敗${NC}"

    echo "ログ確認: docker logs salon-app"

    exit 1

fi

echo ""

echo "================================"

echo -e "${GREEN}✅ デプロイ完了！${NC}"

echo "================================"

echo ""

echo "アクセス確認:"

echo "  http://$(curl -s ifconfig.me):5000"

echo ""

