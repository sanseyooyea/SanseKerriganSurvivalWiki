#!/bin/bash
# KS2 Wiki 部署脚本（无 Docker，直接 Node.js）
set -e

echo "=== KS2 Wiki 部署 ==="

PROJECT_DIR="/opt/ks2-wiki"

# 1. 安装 Node.js 18
if ! command -v node &> /dev/null || [[ $(node -v | cut -d. -f1 | tr -d v) -lt 18 ]]; then
    echo "安装 Node.js 18..."
    curl -fsSL https://npmmirror.com/mirrors/node/v18.20.8/node-v18.20.8-linux-x64.tar.xz | tar -xJ -C /usr/local --strip-components=1
    echo "Node $(node -v) 已安装"
fi

# 2. 安装 PM2
if ! command -v pm2 &> /dev/null; then
    echo "安装 PM2..."
    npm install -g pm2 --registry=https://registry.npmmirror.com
fi

# 3. 检查项目目录
if [ ! -f "$PROJECT_DIR/package.json" ]; then
    echo "错误: 请先将项目文件上传到 $PROJECT_DIR"
    exit 1
fi

cd "$PROJECT_DIR"

# 4. 安装依赖
echo "安装依赖..."
npm ci --registry=https://registry.npmmirror.com

# 5. 构建
echo "构建项目..."
npm run build

# 6. 生成环境变量
if [ ! -f .env ]; then
    echo "JWT_SECRET=$(openssl rand -hex 32)" > .env
    echo "已生成 .env"
fi

# 7. 用 PM2 启动
echo "启动服务..."
pm2 delete ks2-wiki 2>/dev/null || true
PORT=80 pm2 start .output/server/index.mjs --name ks2-wiki
pm2 save
pm2 startup 2>/dev/null || true

echo ""
echo "=== 部署完成 ==="
echo "访问: http://$(curl -s ifconfig.me 2>/dev/null || echo '你的服务器IP')"
echo ""
echo "常用命令:"
echo "  查看状态: pm2 status"
echo "  查看日志: pm2 logs ks2-wiki"
echo "  重启: pm2 restart ks2-wiki"
echo "  停止: pm2 stop ks2-wiki"
