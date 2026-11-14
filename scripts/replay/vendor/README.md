# 录像解析器的随包依赖

服务器（2C2G、国内网络）的 runner 镜像只装 `python3`，不装 pip、不联网拉 PyPI：
解析器的两个纯 Python 依赖直接随部署包带过去，`parse_replay.py` 启动时把它们插到 `sys.path` 最前面。

| 文件 | 版本 | 许可 | 来源 |
|---|---|---|---|
| `sc2reader-1.8.0-py3-none-any.whl` | 1.8.0 | MIT | PyPI（zip 直接导入，不解压）|
| `mpyq.py` | 0.2.5 | BSD-2-Clause（见 `LICENSE.mpyq`）| PyPI sdist 里的单文件模块 |

升级：从 PyPI 下载新版本替换这里的文件，然后跑一遍 `python scripts/replay/parse_replay.py ../ks2_replay -o .replay-tmp/batch`，确认样本全部解析成功。
