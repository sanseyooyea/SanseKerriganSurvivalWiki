#!/bin/bash
# KS2 Wiki 更新脚本（Docker 部署，保留用户数据）
#
# 在服务器项目目录 /opt/ks2-wiki 下运行。
# 前置：已用 scp 把新包上传到 /opt/ks2-wiki-deploy.tar.gz
#
#   scp ks2-wiki-deploy.tar.gz root@your-server-ip:/opt/ks2-wiki-deploy.tar.gz
#   ssh root@your-server-ip 'cd /opt/ks2-wiki && ./update.sh'

set -e

PROJECT_DIR="/opt/ks2-wiki"
TAR_PATH="/opt/ks2-wiki-deploy.tar.gz"
DB_FILE="$PROJECT_DIR/data/wiki.db"

cd "$PROJECT_DIR"

if [ ! -f "$TAR_PATH" ]; then
    echo "错误：未找到部署包 $TAR_PATH"
    echo "请先上传：scp ks2-wiki-deploy.tar.gz root@your-server-ip:$TAR_PATH"
    exit 1
fi

# 1. 备份用户数据库（带时间戳，保险起见）
if [ -f "$DB_FILE" ]; then
    BACKUP="$DB_FILE.bak.$(date +%Y%m%d_%H%M%S)"
    cp "$DB_FILE" "$BACKUP"
    echo "✓ 已备份数据库 -> $BACKUP"
else
    echo "提示：未发现现有数据库，可能是首次部署"
fi

# 2. 解压新包（包内已排除 wiki.db，再加 --exclude 双保险）
echo "解压新版本..."
tar -xzf "$TAR_PATH" \
    --exclude='data/wiki.db' \
    --exclude='data/wiki.db-shm' \
    --exclude='data/wiki.db-wal' \
    --exclude='backups'

# 3. 重新构建并启动
echo "构建镜像..."
docker compose build

echo "重启服务..."
docker compose up -d

# 4. 清理上传包，保留最近 5 个数据库备份
rm -f "$TAR_PATH"
ls -1t "$PROJECT_DIR"/data/wiki.db.bak.* 2>/dev/null | tail -n +6 | xargs -r rm -f

echo ""
echo "=== 更新完成 ==="
docker compose ps
echo ""
echo "查看日志：docker compose logs -f"
echo "访问：https://wiki.ks2.top"
