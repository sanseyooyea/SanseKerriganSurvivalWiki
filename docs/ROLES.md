# 角色与权限

Wiki 有三种用户角色，权限逐级递增。角色存在数据库，每次操作都按**库里当前角色**校验（不信任登录令牌里的旧快照，降权立即生效）。

## 角色一览

| 角色 | 能做什么 |
|---|---|
| **user**（普通用户） | 注册登录、绑定游戏句柄、查询 MMR/积分、评论、提交建议反馈、点赞 |
| **editor**（编辑） | user 全部 + 在线编辑职业**简介/攻略**、编辑 Wiki 文章 |
| **admin**（管理员） | editor 全部 + 用户管理（改角色）、处理反馈、删除内容 |

## 权限边界（重点）

- **editor 在线只能改文案**（职业 description/notes、Wiki 文章），**改不了**属性数值 / 技能 / 兵种——那些走代码 + CI 校验。详见 [DATA_MAINTENANCE.md](DATA_MAINTENANCE.md)。
- **admin 不能把自己降级**（防误操作锁死，后端有自降级保护）。
- 改属性数值这类结构化数据，无论什么角色都走 GitHub（开发者改 seed + PR），见 [../CONTRIBUTING.md](../CONTRIBUTING.md)。

## 怎么获得 editor / admin

角色由 admin 在「用户管理」里设置。流程：

1. 先注册一个普通账号并登录。
2. 联系项目维护者（admin）说明你要维护的内容。
3. admin 在后台把你的账号设为 editor。

> 当前唯一 admin：项目所有者 @sanseyooyea。

## 给开发者：权限在代码里怎么用

- `server/utils/auth.ts`：`requireUser(event)` 取库里最新用户；`requireRole(event, ['admin','editor'])` 校验角色。
- 所有**写端点**都必须经过它们，不要直接信任 token 里的 role。
- 新增写端点时，按最小权限原则选择允许的角色集合。
