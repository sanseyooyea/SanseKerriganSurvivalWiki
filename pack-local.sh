#!/bin/bash
# 本地构建打包：本机跑 nuxt build（16G 内存无压力），把 .output 一起打进包。
# 服务器端用 Dockerfile.runner 部署，只装 better-sqlite3 的 Linux 原生二进制，
# 不在 2G 服务器上跑 nuxt build —— 避免 OOM 假死。
#
# 用法：在项目根目录执行  bash pack-local.sh
# 产物：ks2-wiki-deploy.tar.gz（含 .output，约 100MB+）

set -e
cd "$(dirname "$0")"

NPM="${NPM:-/d/nodejs/npm.cmd}"
TAR_NAME="ks2-wiki-deploy.tar.gz"

echo "=== 1) 本地构建 .output ==="
NUXT_IGNORE_LOCK=1 "$NPM" run build

echo "=== 2) 打包（含 .output；-h 跟随软链接很关键）==="
# -h/--dereference 必须加：nitro 的 .output/server/node_modules 用【绝对路径软链接】
# 指向 .nitro/ 下的实际包（如 entities -> /abs/.../.nitro/entities@8.0.0）。不解引用的话，
# 软链接搬到 Linux 容器里指向不存在的本地路径 → 运行时 Cannot find module。
# 不用裸 --exclude='node_modules'：它会连 .output/server/node_modules 一起误伤。
tar -czhf "$TAR_NAME" \
  --exclude='*/node_modules/.cache' \
  --exclude='*.log' \
  --exclude='./data/wiki.db' \
  --exclude='./data/wiki.db-shm' \
  --exclude='./data/wiki.db-wal' \
  .output package.runner.json Dockerfile.runner Dockerfile.runner.dockerignore docker-compose.runner.yml \
  data scripts public server components pages layouts composables assets \
  nuxt.config.ts package.json package-lock.json tsconfig.json app.vue \
  2>/dev/null || true

SIZE=$(du -h "$TAR_NAME" | cut -f1)
echo ""
echo "已打包: $TAR_NAME ($SIZE)（含本地构建的 .output）"
