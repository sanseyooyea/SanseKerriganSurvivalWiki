# 角色与权限

Wiki 有三种用户角色，权限逐级递增。角色存在数据库，每次操作都按**库里当前角色**校验（不信任登录令牌里的旧快照，降权立即生效）。

## 角色一览

| 角色 | 能做什么 |
|---|---|
| **user**（普通用户） | 注册登录、绑定游戏句柄与邮箱、查询 MMR/积分、评论、提交建议反馈、点赞、**提交** Wiki 文章编辑（进待审队列） |
| **editor**（编辑） | user 全部 + 在线编辑职业**简介/攻略**（直接生效） |
| **admin**（管理员） | editor 全部 + **直接发布** Wiki 文章、审核他人提交的编辑、处理反馈、用户管理（改角色 / 重置密码 / 改句柄）、查看流量统计、删除内容 |

> 第一个注册的账号自动成为 admin，之后注册的都是 user。

## 权限边界（重点）

- **editor 在线只能改文案**（职业 description/notes），**改不了**属性数值 / 技能 / 兵种——那些走代码 + CI 校验。后端会丢弃 description/notes 以外的字段。详见 [DATA_MAINTENANCE.md](DATA_MAINTENANCE.md)。
- **Wiki 文章先审后发**：非 admin（含 editor）保存文章时不会改动线上页面，而是写入待审队列；admin 在管理后台「编辑审核」里并排对比后通过或驳回（可留备注）。投稿人可通过 `GET /api/wiki/reviews/mine` 查到自己的审核结果（前端暂无入口）。若投稿后线上页面已被他人改过，后台会给出黄色警告，通过会覆盖最新版本（覆盖前自动存入修订历史）。
- **admin 不能把自己降级**（防误操作锁死，后端有自降级保护）。
- 改属性数值这类结构化数据，无论什么角色都走 GitHub（开发者改 seed + PR），见 [../CONTRIBUTING.md](../CONTRIBUTING.md)。

## 怎么获得 editor / admin

角色由 admin 在「用户管理」里设置。流程：

1. 先注册一个普通账号并登录。
2. 联系项目维护者（admin）说明你要维护的内容。
3. admin 在后台把你的账号设为 editor。

> 当前唯一 admin：项目所有者 @sanseyooyea。

## 给开发者：权限在代码里怎么用

- `server/utils/auth.ts`：`requireUser(event)` 取库里最新用户；`requireRole(event, ['admin','editor'])` 校验角色。token 里带 `tokenVersion`，改密码 / 管理员重置密码时递增，旧 token 立即失效。
- 所有**写端点**都必须经过它们，不要直接信任 token 里的 role。
- 新增写端点时，按最小权限原则选择允许的角色集合。
