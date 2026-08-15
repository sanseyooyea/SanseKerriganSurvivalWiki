#!/usr/bin/env bash
# KS2 Wiki 定时备份脚本（在服务器 /opt/ks2-wiki 下由 cron 调用）
#
# 只备份唯一不可再生的用户数据：data/wiki.db
# （stats.db / catalog.json / economy 等都能从 map 提取管线重建，不进备份。）
#
# 关键点：wiki.db 是 WAL 模式，最近提交的数据在 -wal 文件里。绝不能裸 cp 单个
# wiki.db —— 会拷到缺最新写入甚至撕裂的文件。这里用 SQLite 联机备份（.backup /
# better-sqlite3 backup），容器在写也能得到一致快照。
#
# 用法：
#   ./scripts/backup.sh              # 打一份快照
#   crontab 每天调用（见 docs/BACKUP.md）
#
# 环境变量（都有默认值）：
#   PROJECT_DIR  项目根目录，默认 /opt/ks2-wiki
#   KEEP         保留最近几份，默认 14（每天一次 ≈ 保留两周）
#   CONTAINER    容器名，默认 ks2-wiki（仅 sqlite3 缺失时的兜底路径用到）

set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/opt/ks2-wiki}"
KEEP="${KEEP:-14}"
CONTAINER="${CONTAINER:-ks2-wiki}"

DB="$PROJECT_DIR/data/wiki.db"
BACKUP_DIR="$PROJECT_DIR/backups"
TS="$(date +%Y%m%d_%H%M%S)"
DEST="$BACKUP_DIR/wiki-$TS.db"

log() { echo "[backup $(date '+%F %T')] $*"; }
fail() { log "错误：$*"; exit 1; }

[ -f "$DB" ] || fail "未找到数据库 $DB"
mkdir -p "$BACKUP_DIR"

# 1) 一致性快照
if command -v sqlite3 >/dev/null 2>&1; then
    # 宿主机有 sqlite3：直接对 bind-mount 的文件做联机备份
    sqlite3 "$DB" ".backup '$DEST'" || fail ".backup 失败"
else
    # 兜底：借容器内必然存在的 better-sqlite3。先写进 bind-mount 的 data/，再挪到 backups/
    log "宿主机无 sqlite3，改用容器内 better-sqlite3 备份"
    TMP_IN_DATA=".bak-$TS.db"
    docker exec "$CONTAINER" node -e "
        require('better-sqlite3')('/app/data/wiki.db')
          .backup('/app/data/$TMP_IN_DATA')
          .then(() => process.exit(0))
          .catch(e => { console.error(e); process.exit(1); })
    " || fail "容器内 better-sqlite3 备份失败"
    mv "$PROJECT_DIR/data/$TMP_IN_DATA" "$DEST"
fi

# 2) 完整性校验（有 sqlite3 才做；坏快照直接丢弃，不进轮转）
if command -v sqlite3 >/dev/null 2>&1; then
    if ! sqlite3 "$DEST" "PRAGMA integrity_check;" | grep -qx "ok"; then
        rm -f "$DEST"
        fail "完整性校验未通过，已丢弃 $DEST"
    fi
fi

# 3) 压缩（wiki.db 很小，gzip 后通常几十 KB）
gzip -f "$DEST"
log "已生成快照 -> $DEST.gz ($(du -h "$DEST.gz" | cut -f1))"

# 4) 轮转：按时间倒序保留最近 KEEP 份，其余删除
#    只匹配本脚本产出的 wiki-*.db.gz，不碰 update.sh 的 wiki.db.bak.* 部署备份
ls -1t "$BACKUP_DIR"/wiki-*.db.gz 2>/dev/null | tail -n "+$((KEEP + 1))" | while read -r old; do
    rm -f "$old"
    log "轮转删除 $old"
done

log "完成。当前保留 $(ls -1 "$BACKUP_DIR"/wiki-*.db.gz 2>/dev/null | wc -l | tr -d ' ') 份快照。"
