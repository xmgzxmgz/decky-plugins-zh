#!/usr/bin/env python3
"""Steam Deck Decky 插件汉化补丁

把已安装的 Decky 插件界面文案替换成中文，所有改动都可一键回滚。

用法：
    sudo python3 zh_patch.py apply     # 汉化（含插件显示名）
    sudo python3 zh_patch.py text      # 只汉化插件内部文案
    sudo python3 zh_patch.py names     # 只改插件显示名
    sudo python3 zh_patch.py restore   # 全部还原英文
    python3 zh_patch.py status         # 查看汉化状态（无需 root）

原理：
    绝大多数 Decky 插件把英文串同时当作 i18n 的 key 和显示值，
    因此把带引号的英文字面量整体替换成中文后，查表与显示会同步变化，
    逻辑不受影响。脚本只替换 translations.json 中人工挑选的界面文案，
    绝不触碰 CSS 属性、SVG 路径、内部接口名等代码标识。

安全措施：
    - 修改前自动备份为 <文件>.zhbak
    - 写入前校验双引号数量与原文一致，不一致则放弃写入
    - 状态值（Disabled/Enabled/Offline 等）刻意不翻译，避免逻辑失效
"""

import json
import os
import shutil
import sys

BACKUP_SUFFIX = ".zhbak"
DEFAULT_ROOT = "/home/deck/homebrew/plugins"
HERE = os.path.dirname(os.path.abspath(__file__))


def load_translations():
    path = os.path.join(HERE, "translations.json")
    if not os.path.exists(path):
        sys.exit(f"找不到翻译表：{path}")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("translations", {}), data.get("plugin_names", {})


def plugin_root():
    root = os.environ.get("DECKY_PLUGIN_ROOT", DEFAULT_ROOT)
    if not os.path.isdir(root):
        sys.exit(f"找不到插件目录：{root}\n可用 DECKY_PLUGIN_ROOT 环境变量指定")
    return root


def patch_text(root, translations):
    """替换 dist/index.js 里的界面文案"""
    changed = 0
    for folder, mapping in translations.items():
        js = os.path.join(root, folder, "dist", "index.js")
        if not os.path.exists(js):
            print(f"  - {folder}：未安装，跳过")
            continue

        bak = js + BACKUP_SUFFIX
        if not os.path.exists(bak):
            shutil.copy2(js, bak)
        src = open(bak, encoding="utf-8", errors="surrogateescape").read()
        out = src
        hits = 0
        for en, zh in mapping.items():
            needle = json.dumps(en, ensure_ascii=False)
            repl = json.dumps(zh, ensure_ascii=False)
            n = out.count(needle)
            if n:
                out = out.replace(needle, repl)
                hits += n

        if hits == 0:
            print(f"  - {folder}：没有匹配到文案（可能已汉化或版本不同）")
            continue
        if out.count('"') != src.count('"'):
            print(f"  ! {folder}：引号数量异常，放弃写入")
            continue

        with open(js, "w", encoding="utf-8", errors="surrogateescape") as f:
            f.write(out)
        print(f"  ✓ {folder}：替换 {hits} 处")
        changed += hits
    print(f"文案替换合计 {changed} 处")


def patch_names(root, names):
    """替换 plugin.json 里的显示名（不影响设置目录）"""
    for folder, zh in names.items():
        pj = os.path.join(root, folder, "plugin.json")
        if not os.path.exists(pj):
            continue
        bak = pj + BACKUP_SUFFIX
        if not os.path.exists(bak):
            shutil.copy2(pj, bak)
        try:
            with open(bak, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"  ! {folder}：plugin.json 解析失败 {e}")
            continue
        data["name"] = zh
        with open(pj, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"  ✓ {folder} → {zh}")


def restore(root, translations, names):
    for folder in list(translations) + [k for k in names if k not in translations]:
        for rel in ("dist/index.js", "plugin.json"):
            target = os.path.join(root, folder, rel)
            bak = target + BACKUP_SUFFIX
            if os.path.exists(bak):
                shutil.copy2(bak, target)
                print(f"  ✓ {folder}/{rel} 已还原")


def status(root, translations, names):
    print(f"插件目录：{root}\n")
    rows = []
    for folder in sorted(set(list(translations) + list(names))):
        d = os.path.join(root, folder)
        if not os.path.isdir(d):
            continue
        js = os.path.join(d, "dist", "index.js")
        zh = 0
        if os.path.exists(js):
            s = open(js, encoding="utf-8", errors="ignore").read()
            zh = sum(1 for c in s if "\u4e00" <= c <= "\u9fff")
        name = folder
        try:
            name = json.load(open(os.path.join(d, "plugin.json"), encoding="utf-8")).get("name", folder)
        except Exception:
            pass
        backup = "已汉化" if os.path.exists(js + BACKUP_SUFFIX) else "未汉化"
        rows.append((folder, name, zh, backup))
    print(f"{'插件目录':<26}{'显示名':<14}{'中文字符':>8}   {'状态'}")
    print("-" * 62)
    for folder, name, zh, backup in rows:
        print(f"{folder:<26}{name:<14}{zh:>8}   {backup}")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "status"
    translations, names = load_translations()
    root = plugin_root()

    if mode == "status":
        status(root, translations, names)
        return

    if os.geteuid() != 0:
        sys.exit("需要 root 权限：sudo python3 zh_patch.py " + mode)

    if mode in ("apply", "text"):
        patch_text(root, translations)
    if mode in ("apply", "names"):
        print("\n插件显示名：")
        patch_names(root, names)
    if mode == "restore":
        restore(root, translations, names)
    if mode not in ("apply", "text", "names", "restore"):
        sys.exit(__doc__)

    print("\n完成。重启 Decky 生效：sudo systemctl restart plugin_loader")


if __name__ == "__main__":
    main()
