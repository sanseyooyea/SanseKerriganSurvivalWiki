# 贡献指南（开发者）

欢迎参与凯瑞甘生存2 Wiki 开发。本文面向**写代码 / 改数据管线**的开发者。
如果你是只更新职业简介、攻略的**数据维护人员**，请看 [docs/DATA_MAINTENANCE.md](docs/DATA_MAINTENANCE.md)。

## 环境搭建

- Node.js 22+
- Python 3.12+（仅在改数据时需要，用于跑数据管线脚本）

```bash
npm install
npm run dev        # http://localhost:3000
```

## 协作流程

1. **从 main 切分支**，不要直接在 main 上改：
   ```bash
   git switch -c feat/你的功能
   ```
2. 改完本地跑通：`npm run build` + `python scripts/validate_data.py`
3. 提 PR 到 main，填写 PR 模板，等 CI 通过 + 至少 1 人 review。
4. **禁止直推 main**（已开启分支保护）。

### commit 规范

`类型: 简述`，类型用 `fix` / `feat` / `data` / `docs` / `chore`，中文描述 OK。例：

```
data: 核查并补全 Energizer 数据
fix: 修复 HTTP 访问下剪贴板复制失效
```

## 数据管线（重要）

职业 / 技能 / 兵种 / 老兵等数据是**从游戏地图提取 + seed 构建**的，**不要直接手改 `data/*.json`**——它们是产物，会被重建覆盖。

### 正确流程

```
改 data/seed/*.json  →  python scripts/build_all.py  →  npm run build 验证
```

`build_all.py` 的顺序：roles → abilities → resolve-tooltips → units → veterancy → technician-economy。
数据来源：`D:\starcraft2\凯瑞甘生存2 最新版.SC2Map`（地图更新后重跑即可刷新）。

### 两个例外

- **`data/economy.json`**：手工维护，**没有 seed**，`build_all.py` 不碰它。
  用脚本改它时务必 `json.dump(..., indent=2, ensure_ascii=False)`——
  缩进写错会导致整个文件重格式化，产生巨型无意义 diff。
- **图标**：稳定，地图职业图标变了才单独跑 `extract_icons.py`。

### 数值优先从地图提取，别硬编码

写数据脚本（如 `build_technician_economy.py`）时，**数值应从地图 catalog / GameStrings 解析，不要手写常量或臆测公式**。
教训：技术员转化产出曾被硬编码成"20%−级序%"递减公式，实际地图是固定 +20%（按钮文本「嬗变100矿物为120矿物」），
与地图脱节且无人发现，直到玩家实测对不上。现已改为正则解析按钮文本，地图调整后重跑即同步。
被动产矿型经济（Jinara/SgtHammer 等）的造价目前仍手工维护在 economy.json，地图改数值后需人工核对——
若反复变动，考虑也做成脚本提取。

### 数据校验

提交前跑 `python scripts/validate_data.py`，它检查：
- 所有 `data/*.json` 是合法 JSON
- roles 引用的技能 id 都在 abilities.json 存在（**防断链**）
- economy 的 hero 对得上 roles，建筑必填字段齐全

CI 也会跑这个，断链等问题会拦在合并前。

## 数据 vs 在线编辑的边界（双轨制）

本项目数据有两条维护路径，**互不重叠**：

| 数据 | 路径 | 谁改 |
|---|---|---|
| 属性数值、技能列表、兵种/建筑数值 | git + seed | 开发者 |
| 职业简介(description)、攻略(notes) | 网页在线编辑 → 数据库 | 数据维护员 |

→ 在线编辑**只能改文案**（description/notes），数值类一律走 git。
这样数值有 CI 校验和 git 审计，文案能让非技术维护者灵活更新，两者不会互相覆盖。
详见 [docs/DATA_MAINTENANCE.md](docs/DATA_MAINTENANCE.md)。

## 前端踩坑（已知）

详见 README「开发注意事项」，简记：
- Tailwind 自定义色板 `kerrigan`/`survivor` **没有 300/400 档**
- **别动态拼接 Tailwind class**（purge 会清掉），用语义 class + scoped CSS
- Wiki 文章排版**不用** prose 插件，在页面 scoped 样式里自定义
- 玩家 MMR 与积分是**两个独立数据源**，各自判空

## 安全红线

- 不硬编码密钥（JWT_SECRET / API key / 密码全走环境变量）
- 写端点用 `requireUser` / `requireRole`（查库取最新 role，不信 token 快照）
- 用户内容 `v-html` 出口必须 `DOMPurify.sanitize`
- 改 `server/` `scripts/` 配置文件需 code owner review（见 CODEOWNERS）
