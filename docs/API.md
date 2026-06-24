# API 文档

所有API基于 Nuxt 3 Server Routes，前缀 `/api`。

## 认证

### POST /api/auth/register
注册新用户。第一个注册的用户自动获得admin角色。

**请求体:**
```json
{
  "username": "string (≥2字符)",
  "password": "string (≥6字符)",
  "handle": "string (可选, 格式: 5-S2-1-xxxxxx)"
}
```

**响应:**
```json
{
  "token": "jwt_token",
  "user": { "id": 1, "username": "xxx", "role": "admin", "handle": "" }
}
```

### POST /api/auth/login
用户登录。

**请求体:**
```json
{ "username": "string", "password": "string" }
```

**响应:** 同注册。

### GET /api/auth/me
获取当前用户信息。需要 Authorization header。

**Header:** `Authorization: Bearer <token>`

**响应:**
```json
{ "user": { "id": 1, "username": "xxx", "role": "admin", "handle": "5-S2-1-xxx" } }
```

### PUT /api/auth/handle
绑定/更换游戏句柄。会验证句柄格式并调用外部API确认玩家存在。

**Header:** `Authorization: Bearer <token>`

**请求体:**
```json
{ "handle": "5-S2-1-1194668" }
```

---

## Wiki

### GET /api/wiki
获取所有Wiki页面列表。

**响应:**
```json
{ "pages": [{ "slug": "xxx", "title": "xxx", "updated_at": "..." }] }
```

### GET /api/wiki/:slug
获取单个Wiki页面内容。

### PUT /api/wiki/:slug
创建或更新Wiki页面。需要editor+权限。

**Header:** `Authorization: Bearer <token>`

**请求体:**
```json
{ "title": "string", "content": "markdown string" }
```

### GET /api/wiki/:slug/history
获取页面编辑历史。

---

## 职业编辑

### GET /api/classes/:id
获取职业的覆盖数据（用户编辑的内容）。无数据返回204。

### PUT /api/classes/:id
保存职业编辑。需要editor+权限。

**Header:** `Authorization: Bearer <token>`

**请求体:**
```json
{
  "description": "string",
  "stats": { "hp": 100, ... },
  "abilities": [{ "nameZh": "", "nameEn": "", "tooltip": "" }],
  "troops": [{ "id": "", "nameZh": "", "hp": 0, ... }],
  "buildings": [...],
  "economy": [...],
  "notes": "markdown"
}
```

---

## 玩家查询

### GET /api/mmr?handle=xxx
查询玩家MMR数据。代理194823.xyz API。

**响应:**
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

### GET /api/credits?handle=xxx
查询玩家积分数据。

**响应:**
```json
{
  "replays": 66,
  "penalty": 0,
  "code": "兑换码字符串",
  "totalCredits": 27484,
  "baseCredits": 132,
  "bonusCredits": 0
}
```

积分计算：Lucy积分 = replays × 2 - penalty × 10

### GET /api/leaderboard
获取天梯排行榜。代理 194823.xyz/api/leaderboard，无参数。

**响应:**
```json
{
  "generated_at": "2026-06-09T16:10:31Z",
  "boards": {
    "kerrigan": [
      { "rank": 1, "display_name": "QAQ", "identity": "贪婪的猛狮#58421", "handles": ["5-S2-1-12463673"], "mmr": 3054, "team_name": "凯瑞甘" }
    ],
    "survivor": [ ... ]
  }
}
```

两个榜单各 50 条，按 `mmr` 降序。`handles[0]` 用于跳转玩家详情或拉取详细数据。

### GET /api/played_like?handle=xxx
查询玩家最近对局的「等效 MMR」（每局实际打出的水平）。数据来自本地只读库 `data/stats.db`（官方网关不暴露此数据，离线从生产库转储生成，见 [STATS_PIPELINE.md](STATS_PIPELINE.md)）。缓存 5 分钟。

句柄经 `handles` 表解析为 `identity`（battle_tag），无绑定则回退句柄本身。`data/stats.db` 缺失时优雅降级返回空 `games`。

**响应:**
```json
{
  "identity": "贪婪的猛狮#58421",
  "through": "2026-06-24 09:02:49",
  "games": [
    { "date": "2026-06-24 04:54:38", "role": "Kerrigan", "team": 1,
      "estimated": 3000, "played_like": 2624.76 }
  ]
}
```

- `games`：最近 50 局，按时间倒序。`role` 为英文枚举名（前端经 `role-name-map.json` 转中文）。
- `estimated`：赛前估值 MMR；`played_like`：该局打出的水平。`played_like > estimated` 即超常发挥。
- `through`：数据截至时点（静态快照，需新转储刷新）。

---

## 评论

### GET /api/comments?slug=xxx
获取页面评论。

### POST /api/comments
发表评论。需要登录。

**请求体:**
```json
{ "page_slug": "string", "content": "string" }
```

---

## 管理

### GET /api/admin/users
获取所有用户列表。需要admin权限。

**Header:** `Authorization: Bearer <token>`

**响应:**
```json
{ "users": [{ "id": 1, "username": "xxx", "role": "admin", "handle": "xxx", "created_at": "..." }] }
```

### PATCH /api/admin/users
修改用户角色。需要admin权限。

**请求体:**
```json
{ "userId": 1, "role": "editor" }
```

---

## 权限说明

| 角色 | 权限 |
|------|------|
| user | 浏览、评论、查询 |
| editor | + 编辑Wiki、编辑职业数据 |
| admin | + 管理用户角色 |
