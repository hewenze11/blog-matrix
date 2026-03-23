#!/bin/bash
# ╔══════════════════════════════════════════════════════════╗
# ║         博客矩阵平台 - 一键部署脚本                       ║
# ║  用法：curl -fsSL https://raw.githubusercontent.com/     ║
# ║        hewenze11/blog-matrix/main/deploy.sh | bash       ║
# ╚══════════════════════════════════════════════════════════╝

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

INSTALL_DIR="/opt/blog-matrix"
REPO_URL="https://github.com/hewenze11/blog-matrix.git"

echo -e "${BLUE}"
echo "╔════════════════════════════════════════╗"
echo "║     博客矩阵平台 一键部署               ║"
echo "║     Blog Matrix Platform Setup         ║"
echo "╚════════════════════════════════════════╝"
echo -e "${NC}"

# ── 检查 Docker ────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
    echo -e "${YELLOW}⚠️  Docker 未安装，正在自动安装...${NC}"
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker && systemctl start docker
    echo -e "${GREEN}✅ Docker 安装完成${NC}"
fi

if ! docker compose version &>/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Docker Compose plugin 未安装，正在安装...${NC}"
    apt-get update -qq && apt-get install -y -qq docker-compose-plugin
fi

echo -e "${GREEN}✅ Docker $(docker --version | cut -d' ' -f3 | tr -d ',') 就绪${NC}"

# ── 拉取代码 ────────────────────────────────────────────────
if [ -d "$INSTALL_DIR/.git" ]; then
    echo -e "${BLUE}📦 更新代码...${NC}"
    cd "$INSTALL_DIR" && git pull origin main
else
    echo -e "${BLUE}📦 克隆代码...${NC}"
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# ── 创建 .env 文件 ──────────────────────────────────────────
if [ ! -f "$INSTALL_DIR/.env" ]; then
    echo -e "${BLUE}⚙️  生成配置文件...${NC}"
    SECRET_KEY=$(openssl rand -hex 32 2>/dev/null || cat /proc/sys/kernel/random/uuid | tr -d '-')
    cat > "$INSTALL_DIR/.env" <<EOF
SECRET_KEY=${SECRET_KEY}
ADMIN_USERNAME=admin
ADMIN_PASSWORD=BlogMatrix2024!
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/afcb8993-243a-4d11-801c-d879da200f07
EOF
    echo -e "${GREEN}✅ 配置文件已生成（密钥已随机化）${NC}"
else
    echo -e "${YELLOW}⚠️  已存在 .env 文件，跳过生成${NC}"
fi

# ── 拉取并启动 ──────────────────────────────────────────────
cd "$INSTALL_DIR"
echo -e "${BLUE}🐳 拉取最新镜像...${NC}"
docker compose pull

echo -e "${BLUE}🚀 启动所有服务...${NC}"
docker compose up -d --remove-orphans

# ── 等待健康 ────────────────────────────────────────────────
echo -e "${BLUE}⏳ 等待服务启动...${NC}"
sleep 8

MAX_WAIT=60
ELAPSED=0
while ! curl -sf http://localhost:8000/health &>/dev/null; do
    if [ $ELAPSED -ge $MAX_WAIT ]; then
        echo -e "${RED}❌ 后端启动超时，请查看日志: docker compose logs backend${NC}"
        exit 1
    fi
    sleep 3
    ELAPSED=$((ELAPSED + 3))
    echo -n "."
done
echo ""

# ── 完成 ────────────────────────────────────────────────────
SERVER_IP=$(curl -sf https://ipinfo.io/ip 2>/dev/null || hostname -I | awk '{print $1}')

echo -e "${GREEN}"
echo "╔════════════════════════════════════════════════╗"
echo "║  ✅  博客矩阵平台部署成功！                      ║"
echo "╠════════════════════════════════════════════════╣"
echo "║  🌐 管理界面:  http://${SERVER_IP}:80           ║"
echo "║  📡 API文档:   http://${SERVER_IP}:80/docs      ║"
echo "║  👤 默认账号:  admin / BlogMatrix2024!          ║"
echo "║                                                ║"
echo "║  ⚠️  请及时修改默认密码！                        ║"
echo "╚════════════════════════════════════════════════╝"
echo -e "${NC}"
echo "常用命令："
echo "  查看日志: docker compose -f $INSTALL_DIR/docker-compose.yml logs -f"
echo "  重启服务: docker compose -f $INSTALL_DIR/docker-compose.yml restart"
echo "  停止服务: docker compose -f $INSTALL_DIR/docker-compose.yml down"
