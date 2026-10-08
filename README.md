# 凯瑞甘生存2 Wiki

星际争霸2自定义地图「凯瑞甘生存2」的社区Wiki，提供职业数据、技能、科技研究、兵种数据库与对战模拟、经济系统、地图地形查询，英雄胜率/平衡性统计，以及玩家MMR/积分/等效MMR查询。

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
- 49个可选职业（另含「随机」与阵亡复活形态「幽灵」）的完整数据：属性、技能、科技研究、兵种与建筑、经济体系
- 属性成长系统（力量/敏捷/智力，每级加成）——**注意：并非所有英雄都有等级系统**，无等级的英雄（如灵魂/晋升者/赫利俄斯/米拉）不显示成长表
- 能量恢复速度（受智力影响）
- **科技研究**：每个生存方英雄的研究科技树（逐级成本/时间/效果，说明里的动态数值已代入地图真实值）
- **兵种与建筑**：按生产树分组（兵种/技能召唤/召唤物/建筑/经济建筑），形态（埋地/攻城/起飞）挂在本体下；分级技能召唤（如定点防御无人机）逐级展示能量、可吸收伤害或火力
- 按阵营（凯瑞甘/生存者）和分类（猎手/建造者/辅助/防御者）筛选

### 兵种数据库 `/units`
- 生存方 + 凯瑞甘方全部单位（800+），可按阵营/类别/属性筛选、按 DPS 与性价比排序
- 单位数据直接从地图解析：造价/人口/生产来源、属性标签（轻甲/重甲/生物…）、完整武器（多段/溅射/属性加成/对空对地）
- DPS 分「对轻甲 / 对重甲 / 对凯瑞甘」三种靶标；凯瑞甘方单位对凯瑞甘方英雄视为友军
- **升级**：攻防科技按战力曲线逐级叠加，额外科技（射程/视野/解锁对空等）单独列出「只研究这一项」的变化
- **获取总成本**：经过变形/合体才能拿到的单位按整条链计价（如重锤军士芬里尔 = 两台坦克升满 + 合体费），并列出每一步
- **对战模拟**（`/units#sim`）：先选英雄再选单位，两边各自配置科技等级，算出首击伤害（护盾/生命）、攻击次数、击杀时间与单挑结论；无法攻击时给出原因（对空/对地、友军、目标属性被排除）
- 无法从地图静态解析的伤害标注「未解析」，不做估算

### 地图地形 `/terrain`
- 多张地形的小地图与可通行区域（地图每次发布会从地形池里重新烘焙一张，这里收录所有见过的版本）
- 石头生成模拟与「石头死区」标注

### 经济系统 `/economy`
- 常规英雄的经济建筑数据：收入/每秒效率/建造费用（晶矿+气体）/回本时间/加速回本
- 投资回报比（每1矿/秒收入的成本），以及跨英雄的**经济投资比排行榜**（`/economy/leaderboard`）
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
- 注册/登录（JWT认证），忘记密码（邮件重置链接）
- 句柄绑定（关联游戏内角色）
- 管理后台（用户管理、内容编辑）
- 深色模式

### 支持本站 `/support`
- 赞助入口与赞助者名单（`data/sponsors.json`）

## 项目结构

```
├── pages/                 # 页面路由
│   ├── index.vue          # 首页
│   ├── login.vue          # 登录/注册
│   ├── settings.vue       # 个人设置（句柄绑定）
│   ├── lookup.vue         # 玩家查询（游客可用）
│   ├── leaderboard.vue    # 天梯排行榜（游客可用）
│   ├── admin.vue          # 管理后台
│   ├── classes/           # 职业系统（含科技研究、兵种与建筑）
│   ├── units/             # 兵种数据库（总览 + 对战模拟）与单位详情
│   ├── terrain/           # 地图地形（多地图 + 石头模拟）
│   ├── support/           # 支持本站（赞助）
│   ├── forgot-password.vue / reset-password.vue  # 忘记密码
│   ├── wiki/              # Wiki文章
│   ├── council/           # 钻石议会（提案投票）
│   ├── changelog/         # 更新日志
│   ├── feedback/          # 建议反馈
│   ├── balance/           # 英雄胜率·平衡性（胜率榜 + 跨版本走势/Meta）
│   ├── player/            # 玩家详情 + 分享图
│   └── economy/           # 经济系统 + 经济投资比排行榜
├── components/            # Vue组件
├── composables/           # 组合式函数（useBalanceData / useMetaHistory / useTechData / useUnitsData 等）
├── utils/
│   └── unitEngine.ts      # 兵种数值引擎：任意科技组合下的单位数值、DPS、对战模拟、升级曲线（前端现算）
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
│   │   ├── veterancy.seed.json
│   │   ├── ability-names.seed.json
│   │   ├── ability-face.seed.json  # 技能显示身份（指令卡按钮面）覆盖，含按英雄覆盖
│   │   └── units.overrides.json    # 兵种自动发现的手工修正（排除 / 补脚本生成单位）
│   ├── roles.json         # 职业定义（49个 + 随机 + 幽灵，由 build_roles 生成）
│   ├── abilities.json     # 技能数据（约250个，由 build_abilities 生成）
│   ├── tech.json          # 科技研究树（由 build_tech 生成）
│   ├── units-v2.json      # 兵种数据库：生产树/武器/升级/获取成本（由 build_units_v2 生成）
│   ├── terrain.json       # 地形索引（由 build_terrain 生成，逐图数据在 public/terrain/）
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
│   ├── icons/             # 职业图标 (64x64)
│   ├── ability-icons/     # 技能图标（build_ability_icons 生成）
│   ├── tech-icons/        # 科技与单位图标（build_tech_icons 生成）
│   ├── maps/ + terrain/   # 地形小地图与逐图地形数据（build_terrain 生成）
├── scripts/               # 数据提取/刷新脚本（一键 build_all.py，见下方"数据刷新流程"）
├── docs/                  # 文档
│   ├── API.md             # API文档
│   ├── DEPLOY.md          # 部署指南
│   ├── STATS_PIPELINE.md  # 对局统计数据管线（胜率/played_like）
│   ├── AUTO_FETCH.md      # 生产库转储自动拉取
│   ├── DATA_MAINTENANCE.md# 数据维护员指南（在线编辑）
│   ├── WIKI_CONVENTIONS.md# Wiki 文章写作约定
│   ├── BACKUP.md          # 服务器数据备份
│   └── ROLES.md           # 角色与权限
├── Dockerfile.runner      # 生产镜像：只装原生依赖，直接用本地构建好的 .output
├── docker-compose.runner.yml
├── pack-local.sh          # 本地 nuxt build + 打部署包（当前部署方式）
├── deploy_paramiko.py     # 上传部署包并在服务器重建容器
└── refresh-and-deploy.sh  # 对局统计一键刷新 + 部署
```

## 数据来源

| 数据 | 来源 |
|------|------|
| 职业/技能/军衔 | `data/seed/` 策划数据 + SC2Map 提取（`scripts/build_all.py`，已脱离 BankEditor） |
| 科技研究 | SC2Map 的 `CAbilResearch` + `CUpgrade` 直接解析（`build_tech.py`） |
| 兵种数据库 | SC2Map 直接解析：从英雄单位沿生产/召唤/变形/合体链自动发现（`build_units_v2.py`），仅 `units.overrides.json` 做手工修正 |
| 地形 | SC2Map 及历史版本地图的 Minimap + 寻路数据（`build_terrain.py`） |
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

`build_all.py` 内部已处理 `PYTHONUTF8` 与 `PYTHONPATH`，按序执行：

`build_roles` → `build_abilities` → `resolve-tooltips` → `build_veterancy` → `build_technician_economy` / `build_nova_economy` / `build_nomad_economy` → `build_tech` → `build_units_v2` → `build_terrain`，最后跑只读的 `sync_hero_skills.py` 漂移检查。

- `economy.json` 大部分人工维护，只有技术员 / 诺娃团队 / 游牧民三个条目由脚本重写。
- `build_units_v2` 依赖 `abilities.json`（技能召唤的名称取自这里），必须排在 `build_abilities` 之后。
- 图标不在 `build_all` 里，地图新增科技/单位后单独跑：`extract_map_icons.py`（地图自带贴图）→ `build_tech_icons.py`（科技与单位图标）→ 再跑一次 `build_units_v2.py`（选上新转出的图标）。图标源是 CascView 从游戏目录导出的 `.dds`，放在仓库外的 `D:/starcraft2/sc2_btn_icons_raw`。
- 角色图标稳定（`public/icons/`），仅当地图职业图标变动时才需单独提取。

### data/seed/（人工维护的策划数据，唯一真源）

| 文件 | 内容 |
|------|------|
| `roles.seed.json` | 49 职业：基础属性(血/速/甲/能量，策划值)、分类、阵营、英雄单位、图标/立绘、描述 key、技能清单 |
| `units.overrides.json` | 兵种自动发现的手工修正：`exclude`（误收的占位单位）、`heroExtra`（脚本生成、生产链上找不到的单位） |
| `ability-face.seed.json` | 技能显示身份覆盖：同一技能在不同英雄指令卡上用不同按钮面时（如亚顿/游牧民借用阿瑞斯的后燃充能），按英雄取正确的名字/图标/说明 |
| `veterancy.seed.json` | 力/敏/智成长（策划值，与地图 CBehaviorVeterancy 不符，以种子为准）。**仅含真有等级系统的英雄**；build_veterancy 会校验各英雄单位是否真挂 veterancy 行为，发现残留误标会告警 |
| `ability-names.seed.json` | 地图无中文名的约 14 个技能的人工兜底名（PrimalSlash、监管者镜像等） |

技能清单、分类、经济这类策划数据改动时，手动编辑对应的 seed 文件即可。

### 脚本说明

- `lib_map.py` — 共用地图层：MPQ 读取、GameStrings 解析、catalog 构建（parent 继承 + BOM 剥离 + `&` 转义）、武器伤害链解析。catalog 现仅驻内存，不再落盘。
- `build_roles.py` — 种子 + 地图 → `roles.json`（基础属性取种子；战斗属性/能量回复从英雄单位武器提取）
- `build_abilities.py` — 种子技能清单 + 地图 GameStrings → `abilities.json`（多策略匹配名称/tooltip；技能名优先取技能自身 Button/Name，按钮 face 仅作最后兜底）
- `resolve-tooltips.py` — 解析 tooltip 里的 `<d ref=...>` 数值占位符
- `lib_tech.py` / `build_tech.py` — 研究科技树 → `tech.json`（逐级成本、动态数值代入、图标）
- `lib_units.py` / `build_units_v2.py` — 兵种数据库 → `units-v2.json`。只存基础数值与升级效果引用；曲线、DPS、性价比、对战模拟都由前端 `utils/unitEngine.ts` 按任意科技组合现算（数据文件因此保持在约 2.5MB）
- `build_*_economy.py` — 各英雄专属经济条目（技术员/诺娃/游牧民等）
- `build_terrain.py` / `harvest_terrains.py` — 地形数据；后者从战网缓存收集历史版本地图
- `build_tech_icons.py` / `extract_map_icons.py` / `build_ability_icons.py` — 图标转换
- `sync_hero_skills.py` / `audit_hero_skills.py` — 英雄技能 seed 与地图指令卡的漂移检查（只读；`--write` 前需人工核对，形态/子单位技能常被误判为废弃）
- `build_veterancy.py` — 种子逐字复制 → `veterancy.json`，并校验各 id 仍存在于地图
- `migrate_to_seed.py` — 一次性迁移脚本（已执行，从当时的 data/*.json 反向生成种子）

> 旧的 BankEditor 耦合脚本（`sync-data.py`/`gen-catalog.py`/`enrich-role-stats.py`/`postprocess-abilities.py`）已被取代，逻辑并入上述新脚本，暂留作对照。旧兵种管线（`build_units.py`/`gen-units.py`/`extract-weapons.py`/`units.seed.json`）已删除，由 `build_units_v2.py` 取代。

完成后用 `npm run build` 验证（期望 EXIT 0）。**若有 dev 服务器在跑**，构建会因 Nuxt dev 锁报 "Another Nuxt dev is already running"。优先用 `NUXT_IGNORE_LOCK=1 npm run build` 让构建与 dev 并存（无需停服务器）；或 git-bash 下 `taskkill //PID <n> //F`（双斜杠）停掉它。

> 注：地图里约 15 个技能（如 PrimalSlash、核打击）确实无中文，保留英文显示；部分施法英雄无普攻武器，故无攻击属性，均属正常。

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

### 一键刷新并部署

日常刷新对局数据推荐用编排脚本，把「拉取转储 → 重建 → 提交 → 推送 → 打包 → 部署」收敛成一条命令：

```bash
KS2_PW=*** bash refresh-and-deploy.sh              # 常规：无新转储则自动跳过部署
KS2_PW=*** bash refresh-and-deploy.sh --force      # 强制重下最新转储再走全流程
KS2_PW=*** bash refresh-and-deploy.sh --no-deploy  # 只刷新+提交+推送，不部署
```

数据无变化时（`fetch_dump.py` 未产生新提交）脚本干净退出，不会白跑打包/部署。

> **为什么不做服务端全自动拉取**：转储在 Google Drive，线上服务器（国内）直连不了，`fetch_dump.py` 依赖本地代理（VPN）才能访问，故拉取只能在本地做。
>
> **为什么刷新数据要重新构建**：`balance.json` / `meta-history.json` 在 `composables/` 里是**构建时 `import`** 进 bundle 的，换磁盘文件不生效，必须重新 `nuxt build`。`stats.db` 则是运行时按路径读取（compose 卷挂载 `./data`），本可单独替换——但一键脚本统一走全量部署以求简单可靠。

详见 [docs/STATS_PIPELINE.md](docs/STATS_PIPELINE.md)（口径与脚本）与 [docs/AUTO_FETCH.md](docs/AUTO_FETCH.md)（自动拉取）。

## 部署

- **服务器**: 阿里云 ECS
- **域名**: wiki.ks2.top
- **容器**: Docker (端口映射 8080:3000)
- **反向代理**: Nginx (宿主机)
- **HTTPS**: Let's Encrypt（certbot nginx 插件，自动续期）

日常部署：本地构建打包后上传，服务器只用 `Dockerfile.runner` 装原生依赖，不在 2G 内存的服务器上跑 `nuxt build`。

```bash
bash pack-local.sh                            # 本地 nuxt build + 打包 ks2-wiki-deploy.tar.gz
KS2_PW=*** python deploy_paramiko.py deploy   # 上传 + 备份数据库 + 重建容器 + 清理旧镜像
```

`deploy_paramiko.py` 只上传现成的包、**不会构建**——改完代码一定先 `pack-local.sh`，否则会把旧包重新发上去（退出码照样是 0）。部署后访问一个本次新增的页面确认生效，不要只看首页 200。

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
