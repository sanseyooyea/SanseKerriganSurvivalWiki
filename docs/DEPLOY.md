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
