
#!/bin/bash

set -e

echo "================================"

echo "DigitalOcean VPS セットアップ開始"

echo "================================"

# カラーコード

RED='\033[0;31m'

GREEN='\033[0;32m'

YELLOW='\033[1;33m'

NC='\033[0m' # No Color

# Step 1: システム更新

echo -e "${YELLOW}[1/8] システム更新中...${NC}"

apt-get update -qq

apt-get upgrade -y -qq

echo -e "${GREEN}✓ システム更新完了${NC}"

# Step 2: 必要なパッケージインストール

echo -e "${YELLOW}[2/8] 基本パッケージインストール中...${NC}"

apt-get install -y -qq \

    ca-certificates \

    curl \

    gnupg \

    lsb-release \

    git \

    ufw \

    htop \

    vim

echo -e "${GREEN}✓ 基本パッケージ完了${NC}"

# Step 3: Dockerインストール

echo -e "${YELLOW}[3/8] Dockerインストール中...${NC}"

if ! command -v docker &> /dev/null; then

    # Docker GPGキー追加

    install -m 0755 -d /etc/apt/keyrings

    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg

    chmod a+r /etc/apt/keyrings/docker.gpg

    

    # Dockerリポジトリ追加

    echo \

      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \

      $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

    

    # Dockerインストール

    apt-get update -qq

    apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    

    # Dockerサービス開始

    systemctl start docker

    systemctl enable docker

    echo -e "${GREEN}✓ Docker インストール完了${NC}"

else

    echo -e "${GREEN}✓ Docker 既にインストール済み${NC}"

fi

# Step 4: nginxインストール

echo -e "${YELLOW}[4/8] nginxインストール中...${NC}"

apt-get install -y -qq nginx

systemctl start nginx

systemctl enable nginx

echo -e "${GREEN}✓ nginx インストール完了${NC}"

# Step 5: Certbot（SSL証明書）インストール

echo -e "${YELLOW}[5/8] Certbot インストール中...${NC}"

apt-get install -y -qq certbot python3-certbot-nginx

echo -e "${GREEN}✓ Certbot インストール完了${NC}"

# Step 6: ファイアウォール設定

echo -e "${YELLOW}[6/8] ファイアウォール設定中...${NC}"

ufw --force enable

ufw allow 22/tcp    # SSH

ufw allow 80/tcp    # HTTP

ufw allow 443/tcp   # HTTPS

ufw allow 5000/tcp  # Flask (一時的)

echo -e "${GREEN}✓ ファイアウォール設定完了${NC}"

# Step 7: 作業ディレクトリ作成

echo -e "${YELLOW}[7/8] 作業ディレクトリ作成中...${NC}"

mkdir -p /opt/salon-app

cd /opt/salon-app

echo -e "${GREEN}✓ ディレクトリ作成完了${NC}"

# Step 8: システム情報表示

echo -e "${YELLOW}[8/8] セットアップ完了確認${NC}"

echo ""

echo "================================"

echo -e "${GREEN}✅ セットアップ完了！${NC}"

echo "================================"

echo ""

echo "インストール済みバージョン:"

echo "- Docker: $(docker --version)"

echo "- Docker Compose: $(docker compose version)"

echo "- nginx: $(nginx -v 2>&1)"

echo "- Certbot: $(certbot --version 2>&1 | head -n1)"

echo ""

echo "次のステップ:"

echo "1. deploy_app.sh を作成して実行"

echo "2. 環境変数を設定"

echo "3. アプリをデプロイ"

echo ""

