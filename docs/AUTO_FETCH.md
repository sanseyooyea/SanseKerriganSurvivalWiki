# 生产库转储自动拉取（Google Drive → 重建 → 提交）

开发组每隔一段时间把新的生产库转储（`*.sql.gz` 的 `pg_dump`，~290MB）传到一个
**需授权**的 Google Drive 共享文件夹。本管线把"手动下载 + 重建统计数据"自动化。

> 这是 [STATS_PIPELINE.md](./STATS_PIPELINE.md) 那条**对局统计管线**的入料自动化：它负责把新转储
> 落到 build 脚本默认读取的路径，然后驱动 `build_balance.py` / `build_stats_db.py`。
> 仍**不**并入 `build_all.py`（那条只依赖地图 + seed）。

## 组成

| 文件 | 作用 |
|---|---|
| `D:\starcraft2\tools\rclone\rclone.exe` | Google Drive 客户端（单文件二进制，免安装免管理员） |
| `scripts/fetch_dump.py` | 编排：列目录→选最新→去重→下载→重建→提交 |
| `D:\starcraft2\tools\fetch_dump.bat` | 无人值守包装器，带日志，供定时任务调用 |
| `D:\starcraft2\tools\.fetch_state.json` | 记住上次下载的 Drive 文件（id+mtime），用于去重（不入库） |
| `D:\starcraft2\tools\fetch_dump.log` | 运行日志 |
| Windows 计划任务 `KS2WikiFetchDump` | 每日定时轮询 |

数据源 Drive 文件夹 ID（**私密**，官方只授权维护者一人）存在仓库外的私有配置
`D:\starcraft2\tools\fetch_config.json`，**绝不入库**。本文与脚本里一律用占位符 `<FOLDER_ID>`。
落地路径（build 脚本默认值）：`D:\starcraft2\ks_prod_no_performance_stats.sql.gz`

```jsonc
// D:\starcraft2\tools\fetch_config.json  (私有，不提交)
{ "folder_id": "<真实文件夹ID>", "proxy": "http://127.0.0.1:7890",
  "remote": "gdrive:", "rclone": "D:\\starcraft2\\tools\\rclone\\rclone.exe" }
```

`fetch_dump.py` 运行时从该文件读 `folder_id`/`proxy`（或环境变量 `KS2_DUMP_FOLDER_ID`），
脚本本身不含任何密钥，因此可安全提交到公开仓库。

## ⚠️ 代理（国内访问 Google 必须）

本机直连 `oauth2.googleapis.com` / `googleapis.com` 会超时（被墙），必须走本地代理
`http://127.0.0.1:7890`（Clash 系统代理）。浏览器走了代理但 rclone CLI 不会自动继承，所以：

- `fetch_dump.py` 已把代理写死在顶部 `PROXY` 常量里，所有 rclone 调用自动走它，
  定时任务无需额外配置。代理端口变了就改这个常量。
- **手动**跑任何 rclone 命令（含授权）时，必须先设环境变量。PowerShell：
  `$env:HTTPS_PROXY="http://127.0.0.1:7890"`；Git Bash：`export HTTPS_PROXY=http://127.0.0.1:7890`。

## 一次性配置：rclone 授权（必须你本人在浏览器里做一次）

文件夹需授权，你的 Google 账号已有读权限。用 rclone 配一个名为 `gdrive` 的远程，
走你自己账号的 OAuth，授权后会把 refresh token 缓存到本地，之后无人值守不再弹浏览器。

在本会话输入框里用 `!` 前缀交互式运行（这样授权浏览器能正常弹出）：

```powershell
$env:HTTPS_PROXY="http://127.0.0.1:7890"; D:\starcraft2\tools\rclone\rclone.exe config
```

按以下顺序回答：

| 提示 | 输入 |
|---|---|
| `n/s/q` | `n`（新建远程） |
| `name>` | `gdrive` |
| `Storage>` | `drive`（输入 `drive` 或对应数字） |
| `client_id>` | 直接回车（用 rclone 默认，足够；如撞限流见下文「自建 client_id」） |
| `client_secret>` | 直接回车 |
| `scope>` | `2`（`drive.readonly` 只读，最小权限） |
| `service_account_file>` | 直接回车 |
| `Edit advanced config?` | `n` |
| `Use auto config?` | `y`（本机有浏览器，自动弹出授权页） |
| 浏览器 | 选你**已被授权**的 Google 账号，允许只读访问 |
| `Configure this as a Shared Drive?` | `n`（这是普通共享文件夹，不是团队盘） |
| `y/e/d` | `y`（确认保存） |
| `q` | 退出 |

> 注意：远程**不要**在配置里写死 `root_folder_id`——`fetch_dump.py` 每次用
> `--drive-root-folder-id` 显式指向那个文件夹，远程保持通用即可。

### 验证授权成功

```powershell
$env:HTTPS_PROXY="http://127.0.0.1:7890"
D:\starcraft2\tools\rclone\rclone.exe lsjson gdrive: --drive-root-folder-id <FOLDER_ID> --files-only
```

能列出文件夹里的 `*.sql.gz` 即配置成功。

## 日常用法

```bash
# 手动触发一次检查（有新转储才下载+重建+提交，否则静默退出）
python scripts/fetch_dump.py

# 仅下载，不重建不提交
python scripts/fetch_dump.py --no-build

# 下载并重建，但提交留给自己
python scripts/fetch_dump.py --no-commit

# 强制重下当前最新（即便 state 说已是最新）
python scripts/fetch_dump.py --force
```

脚本**只 commit、不 push**：拉到新转储重建后会自动 `git add data/balance.json data/stats.db`
并 commit（提交信息带 `dump_through` 日期）。**push / 开 PR / 部署仍由你手动走**
（见 [DEPLOY.md](./DEPLOY.md)），符合仓库协作规范。

## 定时任务

已注册 Windows 计划任务 `KS2WikiFetchDump`，每日运行 `fetch_dump.bat`。
因为脚本幂等（没有新转储就一行日志退出），轮询是安全的。

```bash
# 查看 / 立即手动跑一次 / 删除
schtasks /Query /TN KS2WikiFetchDump /V /FO LIST
schtasks /Run   /TN KS2WikiFetchDump
schtasks /Delete /TN KS2WikiFetchDump /F
```

改时间最简单的方式是删除后用新时间重建（命令见仓库提交记录或下方）。

## 排错

- **`rclone lsjson failed` / 列不出文件**：远程没配好或授权过期。重跑授权：
  `D:\starcraft2\tools\rclone\rclone.exe config reconnect gdrive:`
- **OAuth token 过期**：若 Google 项目处于「测试」发布状态，refresh token 约 7 天失效。
  现象是定时任务突然开始失败、日志报授权错误。处理同上 `config reconnect`。
  长期免维护可自建 client_id 并把项目设为「正式」发布（见下）。
- **下载成功但没提交**：说明重建后 `data/balance.json` / `data/stats.db` 内容没变化
  （同一份转储或数据一致），属正常，日志会写 `data files unchanged — no commit`。
- **查日志**：`D:\starcraft2\tools\fetch_dump.log`。

### 自建 client_id（可选，消除限流与 7 天过期）

rclone 默认 client_id 是全球共享的、有限流。若遇到 `rate limit` 或想长期稳定：
在 Google Cloud Console 建一个 OAuth 桌面客户端、把项目发布状态设为「正式（In production）」，
再在 `rclone config` 时填入自己的 `client_id` / `client_secret`。详见 rclone 官方文档
《Making your own client_id》。
