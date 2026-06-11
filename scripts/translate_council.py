#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""钻石议会提案预翻译脚本（开发机运行，不上生产）。
拉取 194823.xyz 议会数据，把英文 title/description/close_reason 翻成中文，
增量写入 data/council-zh.json（按 proposal_id 索引，已翻译的跳过）。

用法（key 走环境变量，绝不硬编码进文件）：
  PACKY_KEY=sk-xxx PYTHONUTF8=1 /c/Python313/python.exe scripts/translate_council.py
  PACKY_KEY=sk-xxx ... scripts/translate_council.py --force   # 重翻全部
"""
import os, sys, json, time, urllib.request, urllib.error

SRC = "https://194823.xyz/api/proposal_votes_cn.json"
ENDPOINT = "https://www.packyapi.com/v1/messages"
MODEL = "claude-sonnet-4-6"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "council-zh.json")
BATCH = 12

SYS_PROMPT = (
    "你是《星际争霸2》合作地图《凯瑞甘生存2》的游戏文本翻译。"
    "把钻石议会提案的英文翻成简洁、地道的简体中文游戏术语。"
    "保留单位/技能/英雄专有名词的通用译法（如 Defensive Matrix=防御矩阵、Delta Squad=三角洲小队）；"
    "拿不准的专有名词保留英文原文。只翻译，不要解释、不要加注。"
    "输入是 JSON 数组，每项含 id/title/description/close_reason。"
    "输出必须是同样长度的 JSON 数组，每项含 id/title/description/close_reason 的中文，"
    "id 原样返回；空字段返回空串。只输出 JSON，不要任何额外文字或 markdown 代码块。"
)


def http_json(url, data=None, headers=None, timeout=60):
    h = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ks2-wiki-translate"}
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_proposals():
    return http_json(SRC, headers={"Accept": "application/json"}).get("proposals", [])


def translate_batch(items, key):
    payload = json.dumps({
        "model": MODEL,
        "max_tokens": 4096,
        "system": SYS_PROMPT,
        "messages": [{"role": "user", "content": json.dumps(items, ensure_ascii=False)}],
    }).encode("utf-8")
    headers = {
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    resp = http_json(ENDPOINT, data=payload, headers=headers, timeout=120)
    text = "".join(b.get("text", "") for b in resp.get("content", []) if b.get("type") == "text")
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1] if "```" in text[3:] else text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text, strict=False)


def main():
    key = os.environ.get("PACKY_KEY")
    if not key:
        print("ERROR: 未设置环境变量 PACKY_KEY"); sys.exit(2)
    force = "--force" in sys.argv

    out_path = os.path.normpath(OUT)
    store = {"translations": {}}
    if os.path.exists(out_path) and not force:
        store = json.load(open(out_path, encoding="utf-8"))
    trans = store.setdefault("translations", {})

    proposals = fetch_proposals()
    todo = []
    for p in proposals:
        pid = str(p["proposal_id"])
        if pid in trans and not force:
            continue
        todo.append({
            "id": pid,
            "title": p.get("title") or "",
            "description": p.get("description") or "",
            "close_reason": p.get("close_reason") or "",
        })
    print(f"提案总数 {len(proposals)}，待翻译 {len(todo)}")
    if not todo:
        print("无新增，已是最新。"); return

    done = 0
    for i in range(0, len(todo), BATCH):
        batch = todo[i:i + BATCH]
        try:
            res = translate_batch(batch, key)
        except Exception as e:
            print(f"  批次 {i // BATCH + 1} 整批失败({e})，降级逐条重试")
            res = []
            for one in batch:
                try:
                    res.extend(translate_batch([one], key))
                except Exception as e2:
                    print(f"    提案 {one['id']} 翻译失败: {e2}")
                time.sleep(0.3)
        for item in res:
            pid = str(item.get("id"))
            trans[pid] = {
                "title": item.get("title", ""),
                "description": item.get("description", ""),
                "close_reason": item.get("close_reason", ""),
            }
        done += len(res)
        print(f"  已翻译 {done}/{len(todo)}")
        # 边翻边存，中断也不丢
        json.dump(store, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        time.sleep(0.5)

    print(f"完成，写入 {out_path}（共 {len(trans)} 条）")


if __name__ == "__main__":
    main()
