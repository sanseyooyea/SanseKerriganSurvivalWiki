# API 文档

所有 API 基于 Nuxt 3 Server Routes，前缀 `/api`。需要登录的端点使用 Header：

```
Authorization: Bearer <token>
```

鉴权由 `server/utils/auth.ts` 完成：`requireUser` / `requireRole` 每次按**数据库里的当前角色**校验，不信任 token 里的旧快照；token 内含 `tokenVersion`，改密码 / 管理员重置密码后旧 token 立即失效。

错误统一走 `createError`，响应体形如 `{ "statusCode": 400, "message": "..." }`。

---

## 认证 `/api/auth`

### POST /api/auth/register
注册。**第一个注册的用户自动成为 admin**，其余为 user。

```json
{
  "username": "string (≥2字符)",
  "password": "string (≥6字符)",
  "handle": "string (可选, 格式 5-S2-1-xxxxxx)",
  "email": "string (可选, 用于找回密码)"
}
```

响应：`{ "token": "jwt", "user": { "id", "username", "role", "handle", "email" } }`

### POST /api/auth/login
```json
{ "username": "string", "password": "string" }
```
响应同注册。

### GET /api/auth/me
当前用户信息：`{ "user": { "id", "username", "role", "handle", "email" } }`

### PUT /api/auth/handle
绑定/更换游戏句柄（需登录）。校验格式 `^\d+-S2-\d+-\d+$`，并请求 194823.xyz 确认玩家存在。
```json
{ "handle": "5-S2-1-1194668" }
```

### PUT /api/auth/email
绑定/修改邮箱（需登录）。校验格式与唯一性（被他人占用返回 409）。
```json
{ "email": "a@b.com" }
```

### POST /api/auth/forgot-password
发送密码重置邮件。`login` 可以是用户名或邮箱。
```json
{ "login": "用户名或邮箱" }
```
- 无论账号是否存在都返回同一句提示（防用户枚举）。
- 同 IP 15 分钟内最多 5 次，超限 429。
- 未配置 `SMTP_HOST` 时不发信，重置链接打印到服务端日志（开发用）。链接前缀取 `APP_URL`。

### POST /api/auth/reset-password
用邮件里的 token 设置新密码（≥6 位）。成功后 `token_version + 1`（所有旧会话失效），删除该用户全部重置 token，并直接返回新的 `{ token, user }` 自动登录。

---

## Wiki 文章 `/api/wiki`

### GET /api/wiki
文章列表（数组，按更新时间倒序）：
```json
[{ "slug": "xxx", "title": "xxx", "category": "guide", "updated_at": "...", "updated_by": "username" }]
```

### GET /api/wiki/:slug
单篇文章，不存在返回 404。

### PUT /api/wiki/:slug
创建或更新文章（**任何登录用户**都可提交）。
```json
{ "title": "string", "content": "markdown", "category": "guide" }
```
- `slug` 必须匹配 `^[a-z0-9]+(-[a-z0-9]+)*$`，长度 2–80；`category` 必须在允许列表（英雄 kebab 名 + `guide/system/governance/general`，见 [WIKI_CONVENTIONS.md](WIKI_CONVENTIONS.md)），缺省 `general`。
- **admin**：直接发布，旧版本先快照进修订表。响应 `{ "published": true, "slug" }`
- **editor / user**：不改动线上页面，写入待审队列 `wiki_edit_reviews`。响应 `{ "pending": true, "slug" }`

### GET /api/wiki/:slug/history
修订列表（最多 50 条，不含正文）：`{ "revisions": [{ "id", "title", "created_at", "edited_by" }] }`

### GET /api/wiki/revisions/:id
单条修订的完整内容（公开）：`{ "revision": { "id", "page_id", "slug", "title", "content", "created_at", "edited_by" } }`

### 编辑审核

| 端点 | 权限 | 说明 |
|---|---|---|
| `GET /api/wiki/reviews?status=` | admin | 审核列表（不含正文，最多 300 条，待审优先）。`status` 可选 `pending/approved/rejected`。响应 `{ reviews, pending }`，`pending` 为待审总数 |
| `GET /api/wiki/reviews/:id` | admin | 详情：`{ review, current, stale }`。`current` 为当前线上页面（供并排 diff）；`stale=true` 表示投稿后线上页面已被别人改过，通过会覆盖最新内容 |
| `PATCH /api/wiki/reviews/:id` | admin | 审批：`{ "status": "approved" \| "rejected", "admin_note": "可选" }`。已处理过的返回 409。通过时在事务内快照旧版并发布，署名记为投稿人 |
| `GET /api/wiki/reviews/mine` | 登录 | 我提交的编辑及审核状态（最多 100 条） |

---

## 评论

### GET /api/comments?slug=xxx
`{ "comments": [...] }`

### POST /api/comments?slug=xxx
需登录。`{ "content": "string" }`

---

## 职业文案

结构化数据（属性/技能/兵种/经济）只走 git + seed，**在线只能改文案**，见 [DATA_MAINTENANCE.md](DATA_MAINTENANCE.md)。

### GET /api/classes/:id
该职业的在线覆盖数据（`class_overrides`），无数据返回 204。

### PUT /api/classes/:id
editor / admin。只接受两个字段，其余字段静默丢弃：
```json
{ "description": "职业简介（≤4000 字）", "notes": "攻略 Markdown（≤20000 字）" }
```

---

## 玩家数据

### GET /api/mmr?handle=xxx
玩家当前 MMR。缓存 30s。

- **第一数据源**：代理 `194823.xyz/api/player`。
- **离线兜底**：上游 404 / 5xx / 超时 / 返回空体时，读 `data/stats.db` 的 `player_mmr_current`（生产库转储重建的快照），载荷结构相同，额外带 `_snapshot: true` 与 `_through`（快照截至时间）。都查不到时返回 `null`。

```json
{
  "cores": { "survivor": 1542, "kerrigan": 1780 },
  "ranks": {
    "survivor": { "percentile": 54, "tier": "黄金" },
    "kerrigan": { "percentile": 75, "tier": "白金" }
  },
  "roles_survivor": [{ "role_id": 19, "role_name": "Selendis", "mmr": 1863, "wins": 46, "plays": 78, "win_rate": 0.59 }],
  "roles_kerrigan": [...]
}
```

### GET /api/mmr_history?handle=xxx
MMR 历史走势，读 `data/stats.db` 的 `mmr_history`。缓存 5 分钟。库缺失或无记录时返回空数组。
```json
{
  "identity": "Name#1234",
  "through": "2026-11-13 23:00:00",
  "core": [[1718000000, 1500, 1620]],      // [时间戳, 生存者核心分, 凯瑞甘核心分]
  "roles": { "Selendis": [[1718000000, 1800]] }
}
```

### GET /api/played_like?handle=xxx
最近 50 局的「等效 MMR」，读 `data/stats.db`（见 [STATS_PIPELINE.md](STATS_PIPELINE.md)）。缓存 5 分钟。句柄经 `handles` 表解析为 battle_tag，无绑定则回退句柄本身；库缺失时返回空 `games`。

```json
{
  "identity": "贪婪的猛狮#58421",
  "through": "2026-11-13 14:17:54",
  "games": [
    { "date": "2026-11-13 04:54:38", "role": "Kerrigan", "team": 1,
      "estimated": 3000, "played_like": 2624.76 }
  ]
}
```

- `role` 为英文名（前端经 `data/role-name-map.json` 转中文）。
- `estimated` 是赛前估值，`played_like` 是该局打出的水平。

### GET /api/credits?handle=xxx
积分。代理 `194823.xyz/api/credits`，并解码兑换码。
```json
{ "replays": 66, "penalty": 0, "code": "兑换码", "totalCredits": 27484, "baseCredits": 132, "bonusCredits": 0 }
```
`baseCredits = replays × 2 − penalty × 10`，`bonusCredits = Lucy积分 − baseCredits`。

### GET /api/leaderboard
天梯榜，代理 `194823.xyz/api/leaderboard`，缓存 60s。
```json
{
  "generated_at": "2026-06-09T16:10:31Z",
  "boards": {
    "kerrigan": [{ "rank": 1, "display_name": "QAQ", "identity": "贪婪的猛狮#58421", "handles": ["5-S2-1-12463673"], "mmr": 3054, "team_name": "凯瑞甘" }],
    "survivor": [...]
  }
}
```
两榜各 50 条，按 `mmr` 降序。

---

## 社区内容（外部代理）

### GET /api/council
钻石议会提案与投票。代理 `194823.xyz/api/proposal_votes_cn.json`，用 `data/council-zh.json`（`scripts/translate_council.py` 预翻译）覆盖中文字段，译文为空时回退英文。上游失败返回 502。

### GET /api/patchnotes?page=1&page_size=20
更新日志，代理 `194823.xyz/api/patchnotes`，按页缓存。

---

## 建议反馈 `/api/feedback`

分类：`feature` / `bug` / `data` / `other`；状态：`pending` / `accepted` / `done` / `rejected`。

| 端点 | 权限 | 说明 |
|---|---|---|
| `GET /api/feedback?category=&status=` | 公开 | 列表（最多 300 条）：`{ feedback: [{ id, category, title, content, status, admin_note, username, votes, voted, ... }] }`。带 token 时 `voted` 表示我是否点过赞 |
| `POST /api/feedback` | 登录 | `{ title (≤100), content (≤2000), category }` |
| `POST /api/feedback/:id/vote` | 登录 | 切换点赞，返回 `{ votes, voted }` |
| `PATCH /api/feedback/:id` | admin | `{ status?, admin_note? }` |
| `DELETE /api/feedback/:id` | 登录 | admin 可删任意；普通用户只能删自己的（否则 403） |

---

## 管理 `/api/admin`

### GET /api/admin/users
admin。`{ "users": [{ "id", "username", "role", "handle", "created_at" }] }`

### PATCH /api/admin/users
admin。按 `action` 分派（缺省为 `setRole`）：

| action | 请求体 | 说明 |
|---|---|---|
| `setRole` | `{ userId, role }` | `role ∈ admin/editor/user`；不能改自己的角色 |
| `resetPassword` | `{ userId, password }` | ≥6 位，该用户所有会话失效 |
| `setHandle` | `{ userId, handle }` | 空串清空；非空时校验格式并向 194823.xyz 确认存在 |

### GET /api/admin/stats?days=30
admin。流量统计，`days` 范围 7–90。
```json
{ "days": 30, "today": { "pv", "uv" }, "totalPv", "rangePv", "rangeUv", "trend": [{ "day", "pv", "uv" }], "topPages": [{ "path", "pv", "uv" }] }
```
UV 按「访客 + 日」去重，区间 UV 是各日 UV 之和（人次/日），不是绝对独立人数。

---

## 其他

### POST /api/track
访问埋点，无需登录。`{ "path": "/classes/4" }`。会过滤 `/api/`、`/_` 开头的路径和静态资源，机器人 UA 静默丢弃。访客指纹 = IP + UA + 当日盐的哈希。

### GET /sitemap.xml
`server/routes/sitemap.xml.ts` 动态生成：静态页 + 所有职业页（`data/roles.json`）+ 所有单位页（`data/units-v2.json`）。

---

## 权限总览

| 角色 | 权限 |
|------|------|
| 游客 | 浏览全部公开页面、玩家查询、排行榜 |
| user | + 评论、提交反馈/点赞、**提交** Wiki 编辑（进待审队列） |
| editor | + 在线编辑职业简介/攻略（直接生效） |
| admin | + 直接发布 Wiki、审核编辑、处理反馈、用户管理、流量统计 |

详见 [ROLES.md](ROLES.md)。
