# 凯瑞甘生存2 Wiki

星际争霸2自定义地图「凯瑞甘生存2」的社区Wiki，提供职业数据、技能、兵种、经济系统查询，英雄胜率/平衡性统计，以及玩家MMR/积分/等效MMR查询。

**线上地址**: https://wiki.ks2.top

## 技术栈

- **框架**: Nuxt 3 + Vue 3
- **样式**: Tailwind CSS 3.4（自定义主题色：Kerrigan红/Survivor蓝）
- **数据库**: SQLite (better-sqlite3)
- **认证**: JWT + bcryptjs
- **Markdown**: marked
- **截图分享**: html2canvas
- **运行环境**: Node.js 22+
- **部署**: Docker + Nginx 反向代理

## 本地开发

```bash
npm install
npm run dev
```

访问 http://localhost:3000

## 开发注意事项

### Tailwind 自定义色板档位
`tailwind.config.ts` 中 `kerrigan` / `survivor` 自定义色仅有 `50/100/200/500/600/700/800` 档位，**没有 300/400**。使用前确认档位存在，否则 class 不生成颜色。

### 避免动态拼接 Tailwind class
`:class="cond ? 'from-survivor-500 to-survivor-600' : ...'"` 这类**动态拼接**的 class 会被 Tailwind 的 purge 机制清除（静态扫描无法识别），导致样式在生产构建中丢失。需要条件色/渐变时，改用语义 class + 组件 `<style scoped>` 里的真实 CSS。

### Wiki 文章排版
Wiki 文章（`/wiki/[slug]`）的 Markdown 正文排版**未使用** `@tailwindcss/typography`（prose）插件，而是在页面 `<style scoped>` 中用 `:deep()` 自定义实现（终端手册风格 + 自动侧边目录）。修改文章样式时编辑该页面的 scoped 样式，不要依赖 prose 类。

### 外部数据源解耦
玩家 MMR（`/api/mmr`）与积分（`/api/credits`）来自 194823.xyz 的**两个独立数据源**，互不保证同时存在（如外服玩家常无 MMR 但有积分）。前端展示需各自独立判空，不可"无 MMR 即视为玩家不存在"。

## 功能模块

### 职业系统 `/classes`
- 49个职业的完整数据（属性、技能、兵种、经济建筑）
- 属性成长系统（力量/敏捷/智力，每级加成）——**注意：并非所有英雄都有等级系统**，无等级的英雄（如灵魂/晋升者/赫利俄斯/米拉）不显示成长表
- 能量恢复速度（受智力影响）
- 按阵营（凯瑞甘/生存者）和分类（猎手/建造者/辅助/防御者）筛选

### 经济系统 `/economy`
- 常规英雄的经济建筑数据：收入/每秒效率/建造费用（晶矿+气体）/回本时间/加速回本
- 投资回报比（每1矿/秒收入的成本）
- 经济加速机制（时间加速倍率、消耗、持续时间）
- **技术员**：独特的转化型经济（击杀得气 → 转化工厂放大），专属展示组件
- **灵魂**：独特的金融/投资型经济（银行复利、股市/证券交易所、赌场博彩、水晶球运气），
  含**经济路径规划器**——输入矿/气/剩余时间，按已核实的游戏数值推演最优发展路线

### Wiki文章系统 `/wiki`
- Markdown编辑器
- 版本历史与回滚
- 评论系统
- 内置治理文档（开发者行为准则、开发者申请指南）

### 钻石议会 `/council`
- 展示钻石及以上玩家对游戏改动的提案与投票
- 红蓝拔河投票条（赞成/反对实时占比）、按状态筛选（投票中/已实装/已关闭）
- 提案内容自动中文化（预翻译脚本 `scripts/translate_council.py` + 后端 merge）
- 投票方法弹窗：游戏内 `-vote` 指令、投票资格/权重/裁决规则
- 数据源 194823.xyz/api/proposal_votes_cn.json（后端代理 + 缓存）

### 更新日志 `/changelog`
- 分页展示版本更新记录
- 数据源 194823.xyz/api/patchnotes（后端代理 + 缓存）

### 建议反馈 `/feedback`
- 登录用户提交建议/Bug/数据纠错，按分类管理
- 点赞、管理员标记处理进度（待处理/已采纳/已完成/不采纳）+ 回复
- 用户可查看提案进度，全员公开可见

### 英雄胜率 · 平衡性 `/balance`
- **英雄胜率榜**：按已核实的官方口径离线自算的全局英雄胜率，支持时间段（日粒度）与国服/外服筛选
- **跨版本走势**（`/balance/trends`）：英雄胜率随版本变化的曲线 + 版本 Meta（上下场率/使用率）标签页
- 数据来自**生产库转储离线预计算**（`data/balance.json` / `data/meta-history.json`，见「对局统计数据管线」），运行时零外部依赖

### 玩家查询 `/lookup`
- MMR段位查询（游客可用）
- Lucy积分查询
- 角色数据展示

### 天梯排行榜 `/leaderboard`
- 凯瑞甘 / 生存者双榜切换，各取核心分前 50 名
- 前三名领奖台展示（冠军卡片放大 + 皇冠/奖牌）
- 点击任意玩家弹出详情面板：双核心分、段位、主力角色战绩、积分，并可跳转完整资料
- 数据源 194823.xyz/api/leaderboard

### 玩家详情 `/player/[handle]`
- 完整玩家数据展示
- **最近对局等效 MMR**（played_like）：玩家每局打出的等效水平，可按主力角色定位筛选（来自 `data/stats.db`）
- **MMR 历史趋势**（mmr_history）
- 分享图片生成（含角色娘化立绘）
- HTTPS环境复制到剪贴板，HTTP降级为下载PNG

### 用户系统
- 注册/登录（JWT认证）
- 句柄绑定（关联游戏内角色）
- 管理后台（用户管理、内容编辑）
- 深色模式

## 项目结构

```
├── pages/                 # 页面路由
│   ├── index.vue          # 首页
│   ├── login.vue          # 登录/注册
│   ├── settings.vue       # 个人设置（句柄绑定）
│   ├── lookup.vue         # 玩家查询（游客可用）
│   ├── leaderboard.vue    # 天梯排行榜（游客可用）
│   ├── admin.vue          # 管理后台
│   ├── classes/           # 职业系统
│   ├── units/             # 兵种详情
│   ├── wiki/              # Wiki文章
│   ├── council/           # 钻石议会（提案投票）
│   ├── changelog/         # 更新日志
│   ├── feedback/          # 建议反馈
│   ├── balance/           # 英雄胜率·平衡性（胜率榜 + 跨版本走势/Meta）
│   ├── player/            # 玩家详情 + 分享图
│   └── economy/           # 经济系统
├── components/            # Vue组件
├── composables/           # 组合式函数（useBalanceData / useMetaHistory 等）
├── server/api/            # 服务端API
│   ├── auth/              # 认证（登录/注册/用户信息）
│   ├── admin/             # 管理接口
│   ├── classes/           # 职业数据API
│   ├── wiki/              # Wiki文章API
│   ├── feedback/          # 建议反馈API（列表/提交/点赞/管理）
│   ├── mmr.get.ts         # MMR数据（代理 194823.xyz）
│   ├── mmr_history.get.ts # MMR历史趋势（读 data/stats.db）
│   ├── played_like.get.ts # 最近对局等效MMR（读 data/stats.db）
│   ├── credits.get.ts     # 积分数据
│   ├── leaderboard.get.ts # 天梯排行榜（代理 194823.xyz）
│   ├── council.get.ts     # 钻石议会（代理 + 中文 merge）
│   ├── patchnotes.get.ts  # 更新日志（代理 194823.xyz）
│   ├── track.post.ts      # 访问埋点
│   └── comments.ts        # 评论管理
├── data/                  # 静态数据 + SQLite数据库
│   ├── seed/              # 人工维护的策划数据（数据刷新的唯一真源）
│   │   ├── roles.seed.json
│   │   ├── units.seed.json
│   │   ├── veterancy.seed.json
│   │   └── ability-names.seed.json
│   ├── roles.json         # 职业定义（49个，由 build_roles 生成）
│   ├── abilities.json     # 技能数据（191个，由 build_abilities 生成）
│   ├── units.json         # 兵种数据（由 build_units 生成）
│   ├── economy.json       # 常规英雄经济数据（人工维护）
│   ├── technician-economy.json  # 技术员专属转化经济（人工维护）
│   ├── spirit-economy.json # 灵魂专属金融经济：银行/股市/赌场/水晶球（从地图脚本核实）
│   ├── veterancy.json     # 军衔成长数据（由 build_veterancy 生成）
│   ├── balance.json       # 英雄/阵营胜率（由 build_balance 从生产库转储生成）
│   ├── meta-history.json  # 跨版本 Meta 走势（由 build_meta 生成）
│   ├── stats.db           # 对局统计只读库：played_like / mmr_history（由 build_stats_db 生成）
│   └── wiki.db            # SQLite数据库（用户/文章/评论/反馈，运行时写入）
├── public/
│   ├── avatars/           # 48个角色娘化立绘 (1024x1024)
│   └── icons/             # 角色图标 (64x64)
├── scripts/               # 数据提取/刷新脚本（一键 build_all.py，见下方"数据刷新流程"）
├── docs/                  # 文档
│   ├── API.md             # API文档
│   ├── DEPLOY.md          # 部署指南
│   ├── STATS_PIPELINE.md  # 对局统计数据管线（胜率/played_like）
│   ├── AUTO_FETCH.md      # 生产库转储自动拉取
│   ├── DATA_MAINTENANCE.md# 数据维护员指南（在线编辑）
│   └── ROLES.md           # 角色与权限
├── Dockerfile             # Docker构建 (node:22)
├── docker-compose.yml     # Docker编排（端口8080:3000）
└── pack.sh                # 打包脚本
```

## 数据来源

| 数据 | 来源 |
|------|------|
| 职业/技能/兵种/军衔 | `data/seed/` 策划数据 + SC2Map 提取（`scripts/build_all.py`，已脱离 BankEditor） |
| 经济 | `data/economy.json`（常规英雄，人工维护）；技术员 `technician-economy.json`、灵魂 `spirit-economy.json`（灵魂数据从 SC2Map 的 Galaxy 脚本核实） |
| 英雄胜率 / 平衡 | `data/balance.json` + `data/meta-history.json`（从官方生产库转储离线预计算，见「对局统计数据管线」） |
| 等效MMR / MMR历史 | `data/stats.db`（played_like / mmr_history，从生产库转储生成） |
| MMR数据 | 194823.xyz/api/player |
| 积分数据 | 194823.xyz/api/credits |
| 天梯排行榜 | 194823.xyz/api/leaderboard |
| 角色娘化图 | PackyAPI (gpt-image-2) 图生图 |

## 数据刷新流程

数据采用 **种子 + 地图提取** 架构，已**不再依赖 BankEditor**：策划数据（地图里没有干净来源的部分）放在 `data/seed/`，其余数值/文本全部直接从 `凯瑞甘生存2 最新版.SC2Map` 提取。

地图更新后，在项目根目录一条命令重建全部数据：

```bash
python scripts/build_all.py
```

`build_all.py` 内部已处理 `PYTHONUTF8` 与 `PYTHONPATH`，按序执行：`build_roles` → `build_abilities` → `resolve-tooltips` → `build_units` → `build_veterancy`。`economy.json` 为人工维护，不参与重建；角色图标稳定（`public/icons/` 已有 49 张），仅当地图职业图标变动时才需单独提取。

### data/seed/（人工维护的策划数据，唯一真源）

| 文件 | 内容 |
|------|------|
| `roles.seed.json` | 49 职业：基础属性(血/速/甲/能量，策划值)、分类、阵营、英雄单位、图标/立绘、描述 key、技能清单 |
| `units.seed.json` | 每英雄 troops/buildings/economy 的成员归属，并保留旧值作逐字段兜底 |
| `veterancy.seed.json` | 力/敏/智成长（策划值，与地图 CBehaviorVeterancy 不符，以种子为准）。**仅含真有等级系统的英雄**；build_veterancy 会校验各英雄单位是否真挂 veterancy 行为，发现残留误标会告警 |
| `ability-names.seed.json` | 地图无中文名的约 14 个技能的人工兜底名（PrimalSlash、监管者镜像等） |

技能清单、分类、经济这类策划数据改动时，手动编辑对应的 seed 文件即可。

### 脚本说明

- `lib_map.py` — 共用地图层：MPQ 读取、GameStrings 解析、catalog 构建（parent 继承 + BOM 剥离 + `&` 转义）、武器伤害链解析。catalog 现仅驻内存，不再落盘。
- `build_roles.py` — 种子 + 地图 → `roles.json`（基础属性取种子；战斗属性/能量回复从英雄单位武器提取）
- `build_abilities.py` — 种子技能清单 + 地图 GameStrings → `abilities.json`（多策略匹配名称/tooltip；技能名优先取技能自身 Button/Name，按钮 face 仅作最后兜底）
- `resolve-tooltips.py` — 解析 tooltip 里的 `<d ref=...>` 数值占位符
- `build_units.py` — 种子成员 + 地图 → `units.json`（逐字段回退，地图缺失的基础兵种保留种子旧值）
- `build_veterancy.py` — 种子逐字复制 → `veterancy.json`，并校验各 id 仍存在于地图
- `migrate_to_seed.py` — 一次性迁移脚本（已执行，从当时的 data/*.json 反向生成种子）

> 旧的 BankEditor 耦合脚本（`sync-data.py`/`gen-catalog.py`/`gen-units.py`/`enrich-role-stats.py`/`postprocess-abilities.py`/`extract-weapons.py`）已被取代，逻辑并入上述新脚本，暂留作对照。

完成后用 `npm run build` 验证（期望 EXIT 0）。**若有 dev 服务器在跑**，构建会因 Nuxt dev 锁报 "Another Nuxt dev is already running"。优先用 `NUXT_IGNORE_LOCK=1 npm run build` 让构建与 dev 并存（无需停服务器）；或 git-bash 下 `taskkill //PID <n> //F`（双斜杠）停掉它。

> 注：地图里约 15 个技能（如 PrimalSlash、核打击）确实无中文，保留英文显示；部分施法英雄无普攻武器，故无攻击属性，均属正常。技能总数 191（旧版 221，少的 30 个为建造/训练/加点等非战斗菜单按钮，无英雄引用）。

## 对局统计数据管线（胜率 / 等效MMR）

除了上面「地图 + seed」那条管线，Wiki 还有**第二条独立数据管线**，专门产出对局统计（英雄胜率、`played_like` 等效MMR、跨版本 Meta）。官方统计后端（代号 **Lucy**）只对外开放了少量网关端点，全局/聚合胜率与 `played_like` 历史并不暴露，因此这些数据改为**从官方生产库转储离线预计算**成静态文件，随仓库/部署包发布，运行时零外部依赖。

- 数据源：`pg_dump` 转储（`*.sql.gz`，~283MB，**不入库**，由维护者私下保管）。
- 胜率**必须照官方口径算**（去重 `balance_*` 表、`outcome IN (0,1)`、分英雄按 `roles.team == outcome` 判胜），否则与官方对不上。

拿到新转储后手动运行（**不并入 `build_all.py`**）：

```bash
python scripts/build_balance.py    # → data/balance.json（英雄/阵营胜率）
python scripts/build_stats_db.py   # → data/stats.db（played_like / mmr_history）
python scripts/build_meta.py       # → data/meta-history.json（跨版本 Meta 走势）
```

两个纯标准库脚本流式解析 `pg_dump` 的 `COPY ... FROM stdin` 块，内存聚合，无需 Postgres。转储的自动拉取（Google Drive → 重建 → 提交）由 `scripts/fetch_dump.py` + Windows 计划任务 `KS2WikiFetchDump` 处理（需本地代理访问 Google）。

详见 [docs/STATS_PIPELINE.md](docs/STATS_PIPELINE.md)（口径与脚本）与 [docs/AUTO_FETCH.md](docs/AUTO_FETCH.md)（自动拉取）。

## 部署

- **服务器**: 阿里云 ECS
- **域名**: wiki.ks2.top
- **容器**: Docker (端口映射 8080:3000)
- **反向代理**: Nginx (宿主机)
- **HTTPS**: Let's Encrypt (certbot DNS验证)

详见 [docs/DEPLOY.md](docs/DEPLOY.md)

## API文档

详见 [docs/API.md](docs/API.md)

## 参与协作

项目采用**双轨制**维护，两类贡献者各有入口：

- **开发者**（写代码、改数据管线）→ [CONTRIBUTING.md](CONTRIBUTING.md)
  分支 + PR 流程、数据管线（seed → build_all）、CI 校验、安全红线。
- **数据维护人员**（更新职业简介、攻略文案）→ [docs/DATA_MAINTENANCE.md](docs/DATA_MAINTENANCE.md)
  网页在线编辑，只改文案，无需懂代码。
- **角色与权限** → [docs/ROLES.md](docs/ROLES.md)

> 边界：属性数值 / 技能 / 兵种等**结构化数据走 git + seed**（开发者维护，有 CI 校验）；
> 职业简介 / 攻略等**文案走在线编辑**（数据维护员维护）。两者不重叠、不互相覆盖。

## 开源许可

本项目采用 [MIT License](LICENSE) 开源。欢迎社区贡献。

> 注：游戏数据（职业/技能/兵种等）来自《凯瑞甘生存2》地图，版权归地图作者与暴雪所有；本仓库的开源许可仅覆盖本 Wiki 的代码。
