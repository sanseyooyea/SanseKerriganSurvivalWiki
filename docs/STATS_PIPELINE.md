# 对局统计数据管线（胜率 / played_like）

本文面向**开发者**，说明 Wiki 的对局统计数据（英雄胜率、跨版本 Meta 走势、玩家最近对局等效 MMR、MMR 历史、离线 MMR 快照）从哪来、怎么生成、怎么刷新。

> 这是 Wiki 的**第二条数据管线**，独立于 `scripts/build_all.py`（那条从地图 + `data/seed/` 生成职业/技能/兵种）。本条依赖**官方生产库转储**，只在拿到新转储时手动跑。

## 背景：为什么要离线自算

官方有完整的对局统计后端（代号 **Lucy**，录像分析器，源码见 `D:\starcraft2\ksreplayanalyzer-main`），但对外只通过公开网关 `194823.xyz/api/*` 暴露了少量端点：

| 网关已开放 | Wiki 用途 |
|---|---|
| `/api/player` | 单个玩家的核心分 / 段位 / 分英雄胜率（`server/api/mmr.get.ts`） |
| `/api/leaderboard` | 天梯榜（`server/api/leaderboard.get.ts`） |
| `/api/credits` | 积分（`server/api/credits.get.ts`） |
| `/api/proposal_votes_cn.json` | 钻石议会（`server/api/council.get.ts`） |

**网关不暴露**：全局/聚合英雄胜率、阵营大盘胜率、`played_like` 历史、MMR 历史时间序列。网关的 `/api/player` 还会不定期整体故障（对所有句柄返回 404）。Wiki 又无官方 Postgres 访问权。

所以这些数据改为**从官方生产库转储离线预计算**成静态文件，随仓库 / 部署包发布，运行时零外部依赖。

## 数据源：生产库转储

- 文件：`ks_prod_no_performance_stats.sql.gz`（gzip 压缩的 `pg_dump`，2026-11 时约 410MB 且持续增长；**不入库**，由维护者私下保管）。
- 用到的表：
  | 表 | 行数级 | 用途 |
  |---|---|---|
  | `balance_games` | ~34 万 | 去重对局（全局胜率源） |
  | `balance_players` | 数百万 | 分英雄胜率源 |
  | `roles` | ~52 | `role_id` → 英文名 → `team`（0=幸存者/1=凯瑞甘） |
  | `historical_balance` | 数千快照 × 每快照 ~50 行 | 官方平衡报告时间序列（跨版本 Meta 源） |
  | `played_like` | 数万 | 每局玩家"打出的等效 MMR"（identity=battle_tag） |
  | `player_mmrs` | ~8 万 | 当前核心分/英雄分 + pickled 历史（MMR 历史与离线快照源） |
  | `players` | 数百万 | 分英雄场次/胜场（离线快照里的 `roles_*` 战绩） |
  | `handles` | ~8.4 万 | `player_handle` → `battle_tag` |

  > 行数随转储增长，上表为 2026-11 的量级。

## 官方胜率口径（务必照此，否则与官方对不上）

镜像自 Lucy 的 `src/apps/analytics/core/helpers/query.py`：

- 算在**去重的 `balance_*` 表**，不是原始 `games`/`players`。同一局多人上传只算一次。
- 过滤 `WHERE outcome IN (0,1)`：`0`=幸存者胜，`1`=凯瑞甘胜，其它（平局/崩盘）不计入分母。
- **全局阵营胜率**：从 `balance_games` 直接数（一行一局）。
- **分英雄胜率**：从 `balance_players` 数，胜负判定 = `roles.team == outcome`（英雄所在阵营是否取胜）。
- `win_rate` 是 **0~1 小数**，前端 ×100。
- 入库阶段（Lucy 侧）已剔除的脏数据，转储里天然不含：非 matchmaking/premade 模式、银行 bug 黑名单时段、作弊地图、凯瑞甘 >2 的 bug 局。

## 生成脚本

三个脚本纯标准库（`build_stats_db.py` 额外用 `pickle` 解 `player_mmrs.history`），流式解析 `pg_dump` 的 `COPY ... FROM stdin` 块（tab 分隔，`\N`=NULL，`\.` 结束），内存聚合，无需 Postgres。

### `scripts/build_balance.py` → `data/balance.json`

```bash
python scripts/build_balance.py [path/to/dump.sql.gz]   # 默认路径见脚本顶部常量
```

产物（语言中立，按 `role_id`；中文/图标前端用 `data/roles.json` 映射）：

```json
{
  "generated_at": "...",
  "dump_through": "<max datetime_of_game>",
  "low_sample_threshold": 30,
  "global": { "survivor_wins": N, "kerrigan_wins": N, "games": N,
              "survivor_win_rate": 0.xx, "kerrigan_win_rate": 0.xx },
  "heroes": [ { "role_id": 4, "role": "Spirit", "team": 0,
                "plays": N, "wins": N, "win_rate": 0.xxxx, "low_sample": false } ],
  "daily": {
    "days": ["2024-09-05", ...],    // 连续日历日（YYYY-MM-DD），按时间排序
    "regions": ["cn", "intl"],      // cn=国服(China)，intl=外服(欧/美/韩)
    "global":  { "cn": { "s": [每日幸存胜], "k": [每日凯胜] }, "intl": {...} },
    "heroes":  { "4": { "cn": { "p": [每日场次], "w": [每日胜场] }, "intl": {...} }, ... }
  }
}
```

`global`/`heroes` 是**全时段全服**聚合（向后兼容，英雄详情页/职业卡片仍用它）。`daily` 把同样的口径**按日历天 × 服务器分组**预分桶（扁平 per-day 数组，非嵌套 pair，省体积）：前端在所选天区间上跨所选服务器组求和，即可算出任意时间段、国服/外服的胜率——无需为每个时间窗预计算。全时段全服求和恒等于顶层 `global`/`heroes`（已校验）。产物用 compact JSON（2026-11 约 450KB，含 801 天）。

### `scripts/build_stats_db.py` → `data/stats.db`

```bash
python scripts/build_stats_db.py [path/to/dump.sql.gz]
```

只读 SQLite（2026-11 约 70MB），运行时由 `server/api/*` 用 `better-sqlite3` 只读打开；库缺失时各端点优雅降级（返回空）。

| 表 | 内容 | 消费端 |
|---|---|---|
| `handles` | `player_handle` → `battle_tag` | 所有按句柄查询的端点先经它解析 identity |
| `played_like` | 每局 identity / 时间 / 英雄 / 赛前估值 / 等效 MMR | `/api/played_like` |
| `mmr_history` | 每位玩家的核心分序列 `[ts, 生存者, 凯瑞甘]` + 各英雄有效分序列（zlib 压缩 JSON） | `/api/mmr_history` |
| `player_mmr_current` | 每位玩家的当前 MMR 载荷，结构与网关 `/api/player` 一致（含段位百分位、分英雄战绩；zlib 压缩 JSON） | `/api/mmr` 的**离线兜底** |
| `meta` | `played_like_through` / `mmr_history_through` / `player_mmr_current_through` | 前端显示「数据截至」 |

> `identity` 多为 **battle_tag**（如 `Name#1234`），少数是 toon 句柄。按句柄查需经 `handles` 表 `player_handle → battle_tag`，无绑定则回退句柄本身（及其大写形式）。
>
> `player_mmrs.history` 里英雄分存的是**相对核心分的增量**：某快照下英雄有效分 = 该快照同阵营核心分 + 增量。只保留玩家实际玩过（增量曾非 0）的英雄，至少 2 个核心快照才写入历史。

### `scripts/build_meta.py` → `data/meta-history.json`

```bash
python scripts/build_meta.py [path/to/dump.sql.gz]
```

读 `historical_balance`（官方平衡报告，每隔几小时一次快照，自 2023-06 起），**按 ISO 周降采样**（取每周最后一个快照），2026-11 时约 180 个点。每个快照按英文 `role_name` 记录 `winrate`（0~1）、`sample`、`k`、`p`。构建期 `import`，供 `/balance?tab=trends` 的跨版本走势与 Meta 标签页使用。

> 时间轴用 `ds`，**不是**版本号——`games.replay_version` 只是录像格式版本（3/6），与地图补丁无关。

## 前端消费

| 文件 | 用途 |
|---|---|
| `composables/useMetaHistory.ts` | 构建期 `import data/meta-history.json`，供跨版本走势 |
| `composables/useBalanceData.ts` | 构建期 `import data/balance.json`；按 `role_id` 索引，另暴露 `daily` 与 `aggregate(start,end,region)` 天区间×服务器聚合助手、`dayToIndex(date)` |
| `pages/balance/index.vue` | 胜率 hub，标签页：**时段排行**（`BalanceRanking.vue`）+ **跨版本走势**（`BalanceTrends.vue`）。`?tab=trends` 深链 |
| `components/BalanceRanking.vue` | 时段排行：全局阵营胜率 + 分英雄胜率表；**服务器(全部/国服/外服) + 时间段(预设/自定义起止日期，天粒度)筛选** |
| `components/BalanceTrends.vue` | 跨版本走势：`meta-history.json` 折线走势 + 历史快照滑块 + 版本 Meta（上下场率/使用率）标签页 |
| `pages/balance/trends.vue` | 301 重定向到 `/balance?tab=trends`（保留旧链接） |
| `pages/classes/[id]/index.vue` | 英雄详情页胜率块 |
| `components/ClassCard.vue` | 职业列表卡片胜率（样本不足隐藏） |
| `server/api/played_like.get.ts` | 句柄 → 最近 50 局 played_like（读 `data/stats.db`） |
| `server/api/mmr_history.get.ts` | 句柄 → 核心分 / 英雄分历史序列（读 `data/stats.db`） |
| `server/api/mmr.get.ts` | 网关 `/api/player` 故障时回退到 `player_mmr_current`，响应带 `_snapshot` / `_through` |
| `pages/player/[handle].vue` | 玩家页「最近对局 · 等效MMR」「MMR 走势」区块 + 分享图 |

## 刷新流程（拿到新转储时）

日常直接用一键脚本（拉取 → 重建 → 提交 → 推送 → 打包 → 部署，无新转储时自动跳过）：

```bash
KS2_PW=*** bash refresh-and-deploy.sh            # 常规
KS2_PW=*** bash refresh-and-deploy.sh --force    # 强制重下最新转储
KS2_PW=*** bash refresh-and-deploy.sh --no-deploy
```

拉取细节见 [AUTO_FETCH.md](./AUTO_FETCH.md)。等价的手动步骤：

```bash
python scripts/build_balance.py   <新转储路径>
python scripts/build_stats_db.py  <新转储路径>
python scripts/build_meta.py      <新转储路径>
git add data/balance.json data/stats.db data/meta-history.json
git commit -m "data: 刷新对局统计(胜率/played_like)至 <dump_through>"
# 官方数据更新不走 PR：review 无误后直接 git push origin HEAD:main，再部署（docs/DEPLOY.md）
```

## 重要约束

- **静态快照**：数据冻结在转储时点（`balance.json` / `meta-history.json` 的 `dump_through`、`stats.db` 的 `meta.*_through` 标注「数据截至」）。played_like、MMR 历史不会自动更新，必须靠新转储刷新。
- **不并入 `build_all.py`**：那条只依赖地图 + seed；本条依赖偶发的转储。
- **部署**：`data/balance.json`、`data/meta-history.json`、`data/stats.db` 都纳入 git，`pack-local.sh` 打进部署包（排除运行时的 `wiki.db`）。`balance.json` / `meta-history.json` 是**构建期 import**，换文件必须重新 `nuxt build`；`stats.db` 运行时按路径读取（compose 把 `./data` 挂进容器）。
- **未来若官方网关开放** `/winrate/*`、`played_like` 或 MMR 历史：可把数据源从静态文件切到 `server/api/*` 代理（沿用 leaderboard/council 模式），前端无需改。
