# 部署指南

## 线上环境

- 服务器：阿里云 ECS，**2C2G、无 swap**，项目目录 `/opt/ks2-wiki`
- 域名：`wiki.ks2.top`，宿主机 Nginx 反代到容器 `8080:3000`，HTTPS 用 Let's Encrypt（certbot nginx 插件自动续期）
- 容器：`docker-compose.runner.yml`（服务名 `wiki`，容器名 `ks2-wiki`，`mem_limit: 768m`，日志 10MB×3 轮转），`./data` 挂载到 `/app/data`
- Node.js 22（镜像内置）

> ⚠️ **不要在服务器上跑 `nuxt build`**：2G 内存会 OOM，整机磁盘 IO 打满假死，只能控制台重启。
> 所以生产一律走下面的「本地构建部署」。仓库里的 `Dockerfile` / `docker-compose.yml` / `pack.sh` / `update.sh`
> 是服务器端构建的旧方式，只适合内存充足的机器，见文末。

## 环境变量 `.env`

复制 `.env.example` 为 `.env`（已被 `.gitignore` 排除）：

| 键 | 必填 | 说明 |
|---|---|---|
| `JWT_SECRET` | 是 | JWT 签名密钥，生产缺失会拒绝启动。`openssl rand -base64 48` |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASS` / `SMTP_FROM` | 否 | 忘记密码发信。`SMTP_HOST` 为空时不发信，重置链接打到容器日志。端口 465 自动走 SSL |
| `APP_URL` | 否 | 站点公开地址（重置链接前缀，末尾不带 `/`），如 `https://wiki.ks2.top` |

compose 用 `env_file: .env` 把整个文件注入容器。**`deploy` 不会覆盖服务器上的 `.env`**，改了环境变量要单独推：

```bash
KS2_PW='...' python deploy_paramiko.py set-env
```

它只推送本地 `.env` 里的 `SMTP_*` / `APP_URL`（保留服务器上的 `JWT_SECRET` 等其他键），先备份旧 `.env`，经 SFTP 写入（权限 600），同步 `docker-compose.runner.yml` 后 `up -d` 重启。

## 本地构建部署（日常）

```bash
# 1. 本地 nuxt build + 打包 ks2-wiki-deploy.tar.gz
bash pack-local.sh

# 2. 上传 + 远程部署（密码只走环境变量，绝不写进文件）
KS2_PW='服务器密码' python deploy_paramiko.py deploy
```

`pack-local.sh` 内部执行 `NUXT_IGNORE_LOCK=1 npm run build`（可与 dev 服务器并存），然后把 `.output`、`data`（排除 `wiki.db*`）、`public`、`scripts` 及 runner 相关文件打成一个包。2026-11 时包约 320MB，大头是 `data/stats.db`（~70MB）、角色立绘（~86MB）、皮肤 GLB（~45MB）与各类图标。

`deploy_paramiko.py deploy` 的步骤：

1. 预检（目录 / `JWT_SECRET` / docker 版本）
2. SFTP 上传包
3. 备份 `data/wiki.db` → `data/wiki.db.bak.<时间戳>`（裸 cp，仅作部署回滚兜底；定时备份见 [BACKUP.md](BACKUP.md)）
4. 解压，排除 `data/wiki.db*` 与 `backups/`
5. `docker compose -f docker-compose.runner.yml build --pull`——`--pull` 强制拉新 `node:22-slim`，避免复用带漏洞的旧运行时
6. `up -d`
7. 清理：删上传包、`wiki.db.bak.*` 只留最近 5 份、`docker image prune` + `docker builder prune`（悬空镜像堆积曾撑满磁盘，导致 Nginx `ERR_CONTENT_LENGTH_MISMATCH`）

**它只上传现成的包，不会构建**——改完代码一定先跑 `pack-local.sh`，否则会把旧包再发一次，退出码照样是 0。部署后请打开一个本次新增或改动的页面确认生效，不要只看首页返回 200。

### 其他动作

```bash
KS2_PW='...' python deploy_paramiko.py precheck     # 只做预检（默认动作）
KS2_PW='...' python deploy_paramiko.py ps           # 容器状态
KS2_PW='...' python deploy_paramiko.py logs         # 最近 80 行日志
KS2_PW='...' python deploy_paramiko.py set-env      # 推送 SMTP_*/APP_URL，见上
KS2_PW='...' python deploy_paramiko.py push-backup  # 上传 scripts/backup.sh 并立即跑一次
KS2_PW='...' python deploy_paramiko.py cron         # 安装每日 04:17 备份 crontab（幂等）
KS2_PW='...' python deploy_paramiko.py drill        # 用最新备份做一次恢复演练
```

### 对局统计一键刷新 + 部署

```bash
KS2_PW='...' bash refresh-and-deploy.sh
```

拉取新转储 → 重建 `balance.json` / `stats.db` / `meta-history.json` → 提交并直推 main → `pack-local.sh` → `deploy`。无新转储时直接退出。详见 [STATS_PIPELINE.md](STATS_PIPELINE.md)。

### Runner 镜像的三个坑

`Dockerfile.runner` 只做一件事：为 `better-sqlite3` 装 Linux 原生二进制（换了阿里云 apt 源 + npmmirror；预编译包拉不到时用 python3/make/g++ 从源码编译，编完卸掉）。

1. `tar` 必须加 `-h`：nitro 的 `.output/server/node_modules` 是指向 `.nitro/` 的**绝对路径软链接**，不解引用会导致容器里 `Cannot find module`（如 `entities/decode`，表现为 500）。
2. 本地 `.output` 里的 `better_sqlite3.node` 是 Windows 二进制，`Dockerfile.runner` 会用容器内装出的 Linux 版覆盖。
3. 默认 `.dockerignore` 排除了 `.output`，所以 runner 用专属的 `Dockerfile.runner.dockerignore`。

## 首次部署（新服务器）

```bash
# 本地
bash pack-local.sh
scp ks2-wiki-deploy.tar.gz root@服务器IP:/opt/

# 服务器
mkdir -p /opt/ks2-wiki && cd /opt/ks2-wiki
tar -xzf /opt/ks2-wiki-deploy.tar.gz
echo "JWT_SECRET=$(openssl rand -hex 32)" > .env && chmod 600 .env
docker compose -f docker-compose.runner.yml build
docker compose -f docker-compose.runner.yml up -d
```

然后在本地 `KS2_PW=... python deploy_paramiko.py set-env` 推送邮件配置，`cron` 装定时备份，再配好宿主机 Nginx + certbot。访问站点，**第一个注册的用户自动成为 admin**。

## 常用命令（服务器上）

```bash
cd /opt/ks2-wiki
docker compose -f docker-compose.runner.yml ps
docker compose -f docker-compose.runner.yml logs -f
docker compose -f docker-compose.runner.yml restart
docker exec -it ks2-wiki sh
```

## 国内镜像源

Dockerfile 用 `docker.1ms.run` 作为 Docker Hub 代理。失效时替换 `FROM` 前缀，备选 `docker.xuanyuan.me`、`dhub.kubesre.xyz`。测试：`docker pull docker.1ms.run/library/node:22-slim`。

## 旧方式：服务器端构建（仅限内存充足的机器）

```bash
bash pack.sh                                            # 本地打源码包（不含 .output）
scp ks2-wiki-deploy.tar.gz root@IP:/opt/ks2-wiki-deploy.tar.gz
ssh root@IP 'cd /opt/ks2-wiki && ./update.sh'           # 备份 wiki.db → 解压 → docker compose build/up
```

使用 `Dockerfile` + `docker-compose.yml`，在容器里跑 `nuxt build`。**生产服务器不要用。**

## 注意事项

- 分享图片「复制到剪贴板」需要 HTTPS，HTTP 下自动降级为下载 PNG。
- 用户数据只有 `data/wiki.db`（WAL 模式），打包和解压都排除它；其余 `data/` 文件随包覆盖。
- 句柄绑定会请求 194823.xyz 验证玩家是否存在。
