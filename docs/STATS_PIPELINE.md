# 对局统计数据管线（胜率 / played_like）

本文面向**开发者**，说明 Wiki 的对局统计数据（英雄胜率、玩家最近对局等效 MMR）从哪来、怎么生成、怎么刷新。

> 这是 Wiki 的**第二条数据管线**，独立于 `scripts/build_all.py`（那条从地图 + `data/seed/` 生成职业/技能/兵种）。本条依赖**官方生产库转储**，只在拿到新转储时手动跑。

## 背景：为什么要离线自算

官方有完整的对局统计后端（代号 **Lucy**，录像分析器，源码见 `D:\starcraft2\ksreplayanalyzer-main`），但对外只通过公开网关 `194823.xyz/api/*` 暴露了少量端点：

| 网关已开放 | Wiki 用途 |
|---|---|
| `/api/player` | 单个玩家的核心分 / 段位 / 分英雄胜率（`server/api/mmr.get.ts`） |
| `/api/leaderboard` | 天梯榜（`server/api/leaderboard.get.ts`） |
| `/api/credits` | 积分（`server/api/credits.get.ts`） |
| `/api/proposal_votes_cn.json` | 钻石议会（`server/api/council.get.ts`） |

**网关不暴露**：全局/聚合英雄胜率、阵营大盘胜率、`played_like` 历史。Wiki 又无官方 Postgres 访问权。

所以这些数据改为**从官方生产库转储离线预计算**成静态文件，随仓库 / 部署包发布，运行时零外部依赖。

## 数据源：生产库转储

- 文件：`ks_prod_no_performance_stats.sql.gz`（gzip 压缩的 `pg_dump`，~283MB；**不入库**，由维护者私下保管）。
- 用到的表：
  | 表 | 行数级 | 用途 |
  |---|---|---|
  | `balance_games` | ~26 万 | 去重对局（全局胜率源） |
  | `balance_players` | ~260 万 | 分英雄胜率源 |
  | `roles` | 49 | `role_id` → 英文名 → `team`（0=幸存者/1=凯瑞甘） |
  | `played_like` | ~6.4 万 | 每局玩家"打出的等效 MMR"（identity=battle_tag） |
  | `handles` | ~7.9 万 | `player_handle` → `battle_tag` |

## 官方胜率口径（务必照此，否则与官方对不上）

镜像自 Lucy 的 `src/apps/analytics/core/helpers/query.py`：

- 算在**去重的 `balance_*` 表**，不是原始 `games`/`players`。同一局多人上传只算一次。
- 过滤 `WHERE outcome IN (0,1)`：`0`=幸存者胜，`1`=凯瑞甘胜，其它（平局/崩盘）不计入分母。
- **全局阵营胜率**：从 `balance_games` 直接数（一行一局）。
- **分英雄胜率**：从 `balance_players` 数，胜负判定 = `roles.team == outcome`（英雄所在阵营是否取胜）。
- `win_rate` 是 **0~1 小数**，前端 ×100。
- 入库阶段（Lucy 侧）已剔除的脏数据，转储里天然不含：非 matchmaking/premade 模式、银行 bug 黑名单时段、作弊地图、凯瑞甘 >2 的 bug 局。

## 生成脚本

两个脚本纯标准库，流式解析 `pg_dump` 的 `COPY ... FROM stdin` 块（tab 分隔，`\N`=NULL，`\.` 结束），内存聚合，无需 Postgres。

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
                "plays": N, "wins": N, "win_rate": 0.xxxx, "low_sample": false } ]
}
```

### `scripts/build_stats_db.py` → `data/stats.db`

```bash
python scripts/build_stats_db.py [path/to/dump.sql.gz]
```

只读 SQLite（~15MB），表 `played_like` + `handles` + `meta`，对 `identity` / `player_handle` 建索引。运行时 `server/api/played_like.get.ts` 用 `better-sqlite3` 只读查询；缺库时优雅降级（返回空）。

> `played_like.identity` 是 **battle_tag**（如 `Name#1234`），按句柄查需经 `handles` 表 `player_handle → battle_tag`，无绑定则回退句柄本身（大写）。

## 前端消费

| 文件 | 用途 |
|---|---|
| `composables/useBalanceData.ts` | 构建期 `import data/balance.json`，按 `role_id` 索引 |
| `pages/balance/index.vue` | 总览页：全局阵营胜率 + 可排序分英雄胜率表 |
| `pages/classes/[id]/index.vue` | 英雄详情页胜率块 |
| `components/ClassCard.vue` | 职业列表卡片胜率（样本不足隐藏） |
| `server/api/played_like.get.ts` | 句柄 → 最近 50 局 played_like（读 `data/stats.db`） |
| `pages/player/[handle].vue` | 玩家页「最近对局 · 等效MMR」区块 + 分享图 |

## 刷新流程（拿到新转储时）

> 现已自动化：开发组把新转储传到授权 Drive 后，`scripts/fetch_dump.py`（每日计划任务）
> 会自动下载 + 重建 + commit。见 [AUTO_FETCH.md](./AUTO_FETCH.md)。下面是等价的手动步骤。

```bash
python scripts/build_balance.py   <新转储路径>
python scripts/build_stats_db.py  <新转储路径>
git add data/balance.json data/stats.db
git commit -m "data: 刷新对局统计(胜率/played_like)至 <日期>"
# 官方数据更新不走 PR：review 无误后直接 git push origin HEAD:main，再按需部署（docs/DEPLOY.md）
```

## 重要约束

- **静态快照**：数据冻结在转储时点（`balance.json.dump_through`、`stats.db` 的 `meta.played_like_through` 标注「数据截至」）。played_like 的「最近对局」不会自动更新，必须靠新转储刷新。
- **不并入 `build_all.py`**：那条只依赖地图 + seed；本条依赖偶发的转储。
- **部署**：`data/balance.json` 和 `data/stats.db` 已纳入 git（与 `catalog.json` 同类），`pack-local.sh` 打进部署包、`Dockerfile.runner` `COPY data` 上线（解压时排除运行时的 `wiki.db`）。
- **未来若官方网关开放** `/winrate/*` 或 `played_like`：可把数据源从静态文件切到 `server/api/*` 代理（沿用 leaderboard/council 模式），前端无需改。
