#!/bin/bash
# 一键刷新对局数据并部署上线。把原来的手动多步收敛成一条命令：
#
#   fetch_dump.py  →  拉取官方最新 dump（Google Drive，走本地代理）
#                     + 重建 data/{balance.json,stats.db,meta-history.json}
#                     + 若数据有变化则提交【恰好一条】data commit（不 push）
#   ↓  仅当本次产生了新提交才继续（数据无变化则到此为止，不折腾部署）
#   git push       →  data commit 按项目约定直推 origin/main（无需 PR）
#   pack-local.sh  →  本机 nuxt build 打包（balance/meta-history 是构建时 import，
#                     必须重新 build 才能让新数据进 bundle）
#   deploy         →  SFTP 上传 + 服务器 docker compose 重建并重启
#
# 为什么不能「服务端自动拉」：官方 dump 在 Google Drive，阿里云服务器直连不了，
# 拉取只能在有 VPN 的本地做（见 scripts/fetch_dump.py 注释）。本脚本把本地这一串
# 手动操作变成一条命令，这是当前约束下最省事的形态。
#
# 用法（需要服务器部署密码）：
#   KS2_PW=*** bash refresh-and-deploy.sh            # 常规：无新 dump 则不部署
#   KS2_PW=*** bash refresh-and-deploy.sh --force    # 强制重下最新 dump 再走全流程
#   KS2_PW=*** bash refresh-and-deploy.sh --no-deploy  # 只刷新+提交+推送，不部署
#
# 透传给 fetch_dump.py 的参数：--force / --no-build / --no-commit（见该脚本）。
set -euo pipefail
cd "$(dirname "$0")"

: "${KS2_PW:?需要设置 KS2_PW（服务器部署密码）——例：KS2_PW=*** bash refresh-and-deploy.sh}"
PROXY="${HTTPS_PROXY:-http://127.0.0.1:7890}"   # fetch 和 git push 都走它翻墙
PY="${PY:-python}"

# --no-deploy 是本脚本自己的开关，不能透传给 fetch_dump.py；先把它剥掉。
DEPLOY=1
FETCH_ARGS=()
for a in "$@"; do
  if [ "$a" = "--no-deploy" ]; then DEPLOY=0; else FETCH_ARGS+=("$a"); fi
done

before=$(git rev-parse HEAD)

echo "=== 1) 拉取最新 dump + 重建数据 + 提交（无 push） ==="
HTTPS_PROXY="$PROXY" "$PY" scripts/fetch_dump.py "${FETCH_ARGS[@]}"

after=$(git rev-parse HEAD)
if [ "$before" = "$after" ]; then
  echo ""
  echo "数据无变化（HEAD 未移动）——跳过 push / 打包 / 部署。"
  exit 0
fi
echo "新提交: $(git log --oneline -1)"

echo ""
echo "=== 2) 推送 data commit 到 origin/main ==="
git -c http.proxy="$PROXY" -c https.proxy="$PROXY" push origin HEAD:main

if [ "$DEPLOY" = "0" ]; then
  echo ""
  echo "--no-deploy：已刷新并推送，未部署。稍后可执行：KS2_PW=*** $PY deploy_paramiko.py deploy"
  exit 0
fi

echo ""
echo "=== 3) 本地构建打包 ==="
bash pack-local.sh

echo ""
echo "=== 4) 部署到线上 ==="
"$PY" deploy_paramiko.py deploy

echo ""
echo "完成：数据已刷新到 $(git show -s --format=%s HEAD) 并部署上线。"
