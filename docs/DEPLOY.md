# 部署指南

## 环境要求

- 服务器：Linux (推荐 2C2G+)
- Docker + Docker Compose
- 开放端口：8080（或80）
- Node.js 22+（Nuxt 3.21要求，Docker镜像已包含）

## 打包

在本地项目目录执行：

```bash
bash pack.sh
```

生成 `ks2-wiki-deploy.tar.gz`（约86MB，含角色立绘和 catalog 数据），已排除 node_modules、构建产物及用户数据库。

## 首次部署

```bash
# 上传到服务器
scp ks2-wiki-deploy.tar.gz root@服务器IP:/opt/

# SSH到服务器
ssh root@服务器IP
mkdir -p /opt/ks2-wiki && cd /opt/ks2-wiki
tar -xzf /opt/ks2-wiki-deploy.tar.gz

# 生成密钥
echo "JWT_SECRET=$(openssl rand -hex 32)" > .env

# 构建并启动
docker compose build
docker compose up -d
```

访问 `http://服务器IP:8080`，第一个注册的用户自动成为admin。

## 更新部署（保留用户数据）

> ⚠️ **2G 内存服务器必读**：生产服务器内存仅 2G 且无 swap，**不能在容器内跑 `nuxt build`**
> （会 OOM 把整机磁盘 IO 打满假死，需控制台重启）。请改用下方「本地构建部署」。原始的
> 服务器端构建方式（`Dockerfile` + `docker-compose.yml`）仅适合内存充足的机器。

### 本地构建部署（推荐，绕开服务器 OOM）

本机（内存充足）先 `nuxt build` 出 `.output`，打进部署包；服务器端只用 `Dockerfile.runner`
安装唯一的原生依赖 `better-sqlite3`（Linux 预编译二进制），**不在服务器跑 nuxt build**。

```bash
# 1. 本地构建 + 打包（pack-local.sh 内部已 npm run build，并用 tar -h 解引用 nitro 软链接）
bash pack-local.sh

# 2. 上传 + 远程部署（密码走环境变量，绝不写进文件）
KS2_PW='服务器密码' python deploy_paramiko.py deploy
# 也可先 precheck / 查状态 / 看日志：
KS2_PW='...' python deploy_paramiko.py precheck
KS2_PW='...' python deploy_paramiko.py logs
```

关键文件：`Dockerfile.runner`、`Dockerfile.runner.dockerignore`（不排除 `.output`）、
`docker-compose.runner.yml`、`package.runner.json`。三个易踩的坑：
1. `tar` 必须加 `-h`：nitro 的 `.output/server/node_modules` 是指向 `.nitro/` 的**绝对路径软链接**，
   不解引用会导致 Linux 容器里 `Cannot find module`（如 `entities/decode`，表现为 500）。
2. 本地 `.output` 里的 `better_sqlite3.node` 是 Windows 二进制，`Dockerfile.runner` 会用容器内
   `npm install` 出的 Linux 版覆盖它。
3. 默认 `.dockerignore` 排除了 `.output`，所以用专属的 `Dockerfile.runner.dockerignore`。

`deploy_paramiko.py deploy` 会：上传 → 备份 `wiki.db` → 排除用户数据解压 → `docker compose
-f docker-compose.runner.yml build`（仅装原生依赖，秒级）→ `up -d` → 清理。全程不跑 nuxt build。

### 服务器端构建部署（仅限内存充足的机器）

更新流程已封装进 `update.sh`，会自动备份数据库、排除用户数据、重建并重启容器。

**1. 本地打包**

```bash
bash pack.sh
```

`pack.sh` 已排除 `data/wiki.db`（含 `-shm`/`-wal`），打出的包不含任何用户数据。

**2. 上传到服务器**

```bash
scp ks2-wiki-deploy.tar.gz root@your-server-ip:/opt/ks2-wiki-deploy.tar.gz
```

**3. 服务器上执行更新**

```bash
ssh root@your-server-ip 'cd /opt/ks2-wiki && ./update.sh'
```

`update.sh` 会依次：
1. 给 `data/wiki.db` 打一份带时间戳的备份（保留最近 5 份）
2. 解压新包，三重 `--exclude` 确保不覆盖用户数据库
3. `docker compose build` 重建镜像
4. `docker compose up -d` 重启服务
5. 清理上传包与过期备份

关键：用户数据存放在数据卷挂载的 `data/wiki.db`，打包和解压都已排除该文件，更新不会影响已注册账号、绑定句柄、Wiki 文章和评论。

> 首次给 `update.sh` 添加可执行权限：`chmod +x update.sh`（包内已是脚本文件，解压后若无执行位则补一次）。

## Docker镜像拉取问题（国内服务器）

Dockerfile使用 `docker.1ms.run` 作为镜像代理。如果失效，替换Dockerfile中的前缀：

```dockerfile
FROM docker.1ms.run/library/node:22 AS builder
```

可选代理：
- `docker.1ms.run`
- `docker.xuanyuan.me`
- `dhub.kubesre.xyz`

测试哪个可用：`docker pull docker.1ms.run/library/node:22`

## 常用命令

```bash
# 查看状态
docker compose ps

# 查看日志
docker compose logs -f

# 重启
docker compose restart

# 停止
docker compose down

# 进入容器
docker exec -it ks2-wiki sh
```

## 数据备份

数据库文件位于 `/opt/ks2-wiki/data/wiki.db`，定期备份：

```bash
cp /opt/ks2-wiki/data/wiki.db /opt/ks2-wiki/data/wiki.db.bak
```

## 端口修改

编辑 `docker-compose.yml` 中的端口映射：

```yaml
ports:
  - "80:3000"   # 改为80直接访问
```

记得在阿里云安全组放行对应端口。

## 注意事项

- 分享图片的"复制到剪贴板"功能需要HTTPS环境，HTTP下会自动降级为下载PNG
- `public/avatars/` 目录包含48个角色娘化立绘（约85MB），打包时会包含在内
- 首次注册的用户自动成为admin
- 句柄绑定会调用194823.xyz验证玩家是否存在
