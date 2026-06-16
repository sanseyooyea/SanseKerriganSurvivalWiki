#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
迁移核对：在收窄 override 字段（只保留 description/notes）之前，
检查 class_overrides 表里将被丢弃的字段（stats/abilities/troops/buildings/economy）
是否有实质内容，以及与 git base（roles.json）的差异。

用途：上线"双轨收窄"前先在【生产库】跑一次（dry-run），
人工核对差异是否需要先并回 data/seed/，避免页面数据回退。

用法：
  python scripts/migrate_overrides.py --db data/wiki.db          # dry-run，只报告
  python scripts/migrate_overrides.py --db data/wiki.db --prune  # 实际清理被收窄字段（先备份库！）

默认 dry-run，绝不改库。--prune 才会写。
"""
import argparse
import json
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')

# 收窄后保留的字段；其余将被丢弃
KEEP = {'description', 'notes'}
DROP = ['stats', 'abilities', 'troops', 'buildings', 'economy']


def load_roles():
    with open(os.path.join(DATA, 'roles.json'), encoding='utf-8') as f:
        return {r['id']: r for r in json.load(f)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default=os.path.join(DATA, 'wiki.db'))
    ap.add_argument('--prune', action='store_true',
                    help='实际清理被收窄字段（默认只 dry-run 报告）')
    args = ap.parse_args()

    if not os.path.exists(args.db):
        print(f'数据库不存在: {args.db}')
        sys.exit(1)

    roles = load_roles()
    conn = sqlite3.connect(args.db)
    rows = conn.execute(
        'SELECT class_id, data, updated_by FROM class_overrides').fetchall()

    print(f'共 {len(rows)} 条 override。\n')
    needs_attention = []

    for class_id, raw, updated_by in rows:
        # class_id 可能存成字符串或数字
        cid = int(class_id) if str(class_id).isdigit() else class_id
        data = json.loads(raw)
        base = roles.get(cid, {})
        name = base.get('nameEn', f'id={class_id}')

        dropped = {k: data[k] for k in DROP if k in data and data[k] not in (None, {}, [])}
        if not dropped:
            print(f'✓ {name}(class_id={class_id}): 仅含文案字段，收窄无影响')
            continue

        # 有实质内容将被丢弃 → 需人工核对
        needs_attention.append((class_id, name))
        print(f'⚠ {name}(class_id={class_id}, updated_by={updated_by}): '
              f'以下字段将被丢弃，请核对是否需并回 seed：')
        for k, v in dropped.items():
            if k == 'stats':
                base_stats = base.get('stats', {})
                diff = {sk: (sv, base_stats.get(sk)) for sk, sv in v.items()
                        if base_stats.get(sk) != sv}
                if diff:
                    print(f'    stats 与 base 不一致 (override→base): '
                          f'{json.dumps(diff, ensure_ascii=False)}')
                else:
                    print('    stats 与 base 一致（可安全丢弃）')
            elif k == 'abilities':
                print(f'    abilities: override 有 {len(v)} 条自定义技能')
            else:
                print(f'    {k}: {len(v)} 条')
        print()

    if args.prune:
        print('\n=== --prune：开始清理被收窄字段 ===')
        for class_id, raw, _ in rows:
            data = json.loads(raw)
            clean = {k: v for k, v in data.items() if k in KEEP}
            conn.execute(
                'UPDATE class_overrides SET data = ? WHERE class_id = ?',
                (json.dumps(clean, ensure_ascii=False), class_id))
        conn.commit()
        print('已清理。')
    else:
        if needs_attention:
            print(f'=== {len(needs_attention)} 条需人工核对 ===')
            print('核对后如需保留某些数值，先把它们并回 data/seed/ 并 build_all，'
                  '再用 --prune 清理 override。')
        else:
            print('=== 所有 override 仅含文案，可直接收窄，无需迁移 ===')

    conn.close()


if __name__ == '__main__':
    main()
