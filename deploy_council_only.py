#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""轻量部署：只把 data/council-zh.json 传到服务器卷挂载目录 + 重启容器清缓存。
council-zh.json 是【运行时 readFileSync 读 + ./data:/app/data 卷挂载】，
所以换单文件即生效，无需重打 255M 包 / 重新 build。

用法：KS2_PW=*** /c/Python313/python.exe deploy_council_only.py
"""
import os
from deploy_paramiko import connect, run, PROJECT

LOCAL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "council-zh.json")
REMOTE = f"{PROJECT}/data/council-zh.json"

c = connect()
try:
    print(f"=== 上传 council-zh.json -> {REMOTE} ===")
    sftp = c.open_sftp()
    sftp.put(LOCAL, REMOTE)
    sftp.close()
    print("uploaded")
    print("=== 重启容器清 180s 缓存 ===")
    run(c, f"cd {PROJECT} && docker compose -f docker-compose.runner.yml restart", stream=True)
    run(c, f"cd {PROJECT} && docker compose -f docker-compose.runner.yml ps")
finally:
    c.close()
print("council-only deploy done")
