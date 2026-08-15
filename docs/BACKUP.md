# 备份与恢复

## 备份什么

只备份 **`data/wiki.db`** —— 唯一不可再生的用户数据（账号、Wiki 文章与修订、评论、反馈、投票、流量统计）。

其余数据文件（`stats.db`、`catalog.json`、各 economy / units / balance JSON）都能从 map 提取管线重新生成，**不进备份**。

> WAL 注意：`wiki.db` 是 WAL 模式，最新提交的数据在 `-wal` 文件里。**不要**用 `cp` 拷单个
> `wiki.db`，会拿到缺最新写入甚至撕裂的文件。`backup.sh` 用 SQLite 联机备份（`.backup`），
> 容器在写也能得到一致快照。

## 备份怎么跑

脚本：`scripts/backup.sh`（在服务器 `/opt/ks2-wiki` 下运行）。

- 一致性快照：优先用宿主机 `sqlite3 .backup`；宿主机没装 sqlite3 时兜底调用容器内 `better-sqlite3`。
- 完整性校验：`PRAGMA integrity_check`，坏快照直接丢弃、不进轮转。
- 压缩 + 轮转：gzip 后存到 `/opt/ks2-wiki/backups/wiki-<时间戳>.db.gz`，按时间保留最近 `KEEP`（默认 14）份。

手动跑一次：

```bash
cd /opt/ks2-wiki && ./scripts/backup.sh
```

首次赋可执行权限：`chmod +x scripts/backup.sh`。
建议装 sqlite3 以启用完整性校验：`apt-get install -y sqlite3`（Debian/Ubuntu）。

### 定时（每天一次）

服务器上 `crontab -e` 加一行（凌晨 4:17 低峰跑，日志留档）：

```cron
17 4 * * * cd /opt/ks2-wiki && ./scripts/backup.sh >> /opt/ks2-wiki/backups/backup.log 2>&1
```

改保留份数：`KEEP=30 ./scripts/backup.sh`，或在 cron 行前加 `KEEP=30`。

## 恢复

> ⚠️ 恢复会覆盖当前数据库。务必先停容器，并把当前 `wiki.db` 另存一份保命。

```bash
cd /opt/ks2-wiki

# 1. 停服务，避免写入竞争
docker compose -f docker-compose.runner.yml down     # 或 docker compose down

# 2. 保命：先把现有数据库挪走（连 WAL/SHM 一起）
mkdir -p /tmp/wiki-before-restore
mv data/wiki.db data/wiki.db-wal data/wiki.db-shm /tmp/wiki-before-restore/ 2>/dev/null || true

# 3. 选一份快照解压回去（换成你要恢复的时间戳）
gunzip -c backups/wiki-20260815_041700.db.gz > data/wiki.db

# 4. 校验完整性（有 sqlite3 时）
sqlite3 data/wiki.db "PRAGMA integrity_check;"    # 期望输出 ok

# 5. 起服务
docker compose -f docker-compose.runner.yml up -d
```

恢复出的是一个已合并 WAL 的完整单文件；启动后 SQLite 会重新建 `-wal`/`-shm`，无需手动处理。

## 恢复演练（务必做一次）

没验证过的备份等于没有。挑最新一份快照走一遍：

```bash
gunzip -c backups/$(ls -1t backups/wiki-*.db.gz | head -1 | xargs basename) > /tmp/drill.db
sqlite3 /tmp/drill.db "PRAGMA integrity_check; SELECT count(*) FROM users; SELECT count(*) FROM wiki_pages;"
rm -f /tmp/drill.db
```

能读出用户数和文章数即视为通过。

## 已知局限

- **只做本机轮转**：备份和线上库在同一台机器同一块盘。可防误删、误改、DB 损坏、坏部署，
  **防不了整机/磁盘丢失**。等有第二台机器或对象存储时，再给 `backup.sh` 末尾加一步把
  `backups/` 最新快照推到异地（rsync-over-SSH 或 rclone）。
- 部署时 `update.sh` / `deploy_paramiko.py` 另有一份 `wiki.db.bak.<时间戳>` 部署前快照
  （裸 cp，仅作部署回滚兜底），与本套定时备份相互独立、互不覆盖。
