#!/bin/bash
# 打包部署文件（排除 node_modules 等大目录）
# 在项目根目录执行，生成 ks2-wiki-deploy.tar.gz

set -e

TAR_NAME="ks2-wiki-deploy.tar.gz"

tar -czf "$TAR_NAME" \
  --exclude='node_modules' \
  --exclude='.output' \
  --exclude='.nuxt' \
  --exclude='.git' \
  --exclude='tmp_cache' \
  --exclude='.npm-cache' \
  --exclude='*.log' \
  --exclude='data/wiki.db' \
  --exclude='data/wiki.db-shm' \
  --exclude='data/wiki.db-wal' \
  --exclude='backups' \
  --exclude="$TAR_NAME" \
  .

SIZE=$(du -h "$TAR_NAME" | cut -f1)
echo "已打包: $TAR_NAME ($SIZE)"
echo ""
echo "上传到服务器:"
echo "  scp $TAR_NAME root@你的服务器IP:/opt/ks2-wiki.tar.gz"
echo ""
echo "服务器上解压并部署:"
echo "  mkdir -p /opt/ks2-wiki && cd /opt/ks2-wiki"
echo "  tar -xzf /opt/ks2-wiki.tar.gz"
echo "  chmod +x deploy.sh && ./deploy.sh"
