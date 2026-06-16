#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KS2 Wiki 数据校验 — CI 与本地都可跑。

检查项：
  1. 所有 data/*.json 是合法 JSON
  2. roles.json 每个 role 的 abilities[] id 都能在 abilities.json 找到（防断链）
  3. economy.json 的 hero 都能对上某个 role 的 nameEn；building 必填字段齐全
  4. roles 的 id 唯一、nameEn 唯一

发现问题时打印并以非 0 退出码结束（CI 失败）。
用法：python scripts/validate_data.py   （在 Wiki 根目录运行）
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')

errors = []
warnings = []


def err(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


def load(name):
    """加载 data/<name>，JSON 非法时记错并返回 None。"""
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        err(f'{name}: 文件不存在')
        return None
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        err(f'{name}: JSON 解析失败 — {e}')
        return None


def main():
    # 1) 所有 data/*.json 合法
    json_files = [f for f in os.listdir(DATA) if f.endswith('.json')]
    data = {}
    for name in sorted(json_files):
        d = load(name)
        if d is not None:
            data[name] = d
    # seed 也校验合法性
    seed_dir = os.path.join(DATA, 'seed')
    if os.path.isdir(seed_dir):
        for name in sorted(os.listdir(seed_dir)):
            if name.endswith('.json'):
                try:
                    with open(os.path.join(seed_dir, name), encoding='utf-8') as f:
                        json.load(f)
                except json.JSONDecodeError as e:
                    err(f'seed/{name}: JSON 解析失败 — {e}')

    roles = data.get('roles.json')
    abilities = data.get('abilities.json')
    economy = data.get('economy.json')

    # 2) 技能断链检查
    if roles is not None and abilities is not None:
        ability_ids = set(abilities.keys())
        for r in roles:
            for aid in r.get('abilities', []):
                if aid not in ability_ids:
                    err(f"断链: 职业 {r.get('nameEn')}(id {r.get('id')}) "
                        f"引用了技能 '{aid}'，但 abilities.json 里不存在")

    # 3) roles id / nameEn 唯一
    if roles is not None:
        seen_id, seen_en = {}, {}
        for r in roles:
            rid, en = r.get('id'), r.get('nameEn')
            if rid in seen_id:
                err(f"职业 id 重复: {rid}（{seen_id[rid]} 与 {en}）")
            seen_id[rid] = en
            if en in seen_en:
                err(f"职业 nameEn 重复: {en}")
            seen_en[en] = rid

    # 4) economy 校验
    # 注：economy 的 hero 不一定是职业。有些是特殊游戏机制（如 Ghost = 角色
    # 死亡后的幽灵形态 SCV 经济），它们对不上 roles 是正常的，列入白名单不报警。
    NON_ROLE_ECONOMY = {'Ghost'}
    if economy is not None and roles is not None:
        role_names = {r.get('nameEn') for r in roles}
        role_names_zh = {r.get('nameZh') for r in roles}
        for e in economy:
            hero = e.get('hero')
            if (hero not in role_names and hero not in role_names_zh
                    and hero not in NON_ROLE_ECONOMY):
                warn(f"economy.json 的 hero '{hero}' 在 roles.json 找不到对应职业"
                     f"（若是特殊机制非职业，请加入 validate 的 NON_ROLE_ECONOMY 白名单）")
            for b in e.get('buildings', []):
                for field in ('id', 'nameZh', 'cost'):
                    if field not in b or b[field] is None:
                        err(f"economy {hero} 的建筑 '{b.get('id', '?')}' "
                            f"缺少必填字段 '{field}'")

    # 输出
    for w in warnings:
        print(f'[WARN] {w}')
    for e in errors:
        print(f'[ERROR] {e}')

    if errors:
        print(f'\n校验失败：{len(errors)} 个错误，{len(warnings)} 个警告。')
        sys.exit(1)
    print(f'校验通过（{len(warnings)} 个警告）。检查了 {len(json_files)} 个 JSON 文件、'
          f'{len(roles) if roles else 0} 个职业。')


if __name__ == '__main__':
    main()
