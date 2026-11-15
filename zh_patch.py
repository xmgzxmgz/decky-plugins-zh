#!/usr/bin/env python3
"""Steam Deck Decky 插件汉化补丁

把已安装的 Decky 插件界面文案替换成中文，所有改动都可一键回滚。

用法：
    sudo python3 zh_patch.py apply     # 汉化插件内部文案
    sudo python3 zh_patch.py restore   # 还原英文
    sudo python3 zh_patch.py doctor    # 体检：修复插件名与前端 manifest 不一致
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
    - manifest 块被整体保护，不会因为文案替换而被改动

⚠️ 绝对不要修改 plugin.json 的 name 字段
    Decky 的 IPC 用 plugin.json 的 name 作为路由键，而插件前端打包时
    把 `const manifest = {"name": "..."}` 写死在了 dist/index.js 里。
    两者一旦不一致，前端所有后端调用都会永久挂起 —— 表现为界面一直
    显示「加载中…」、开关点了没反应、退出面板再进显示已关闭，但内核
    其实在正常运行。用 doctor 子命令可以检测并修复。
"""

import json
import os
import re
import shutil
import sys

BACKUP_SUFFIX = ".zhbak"
DEFAULT_ROOT = "/home/deck/homebrew/plugins"
HERE = os.path.dirname(os.path.abspath(__file__))

MANIFEST_RE = re.compile(r"const manifest = (\{.*?\});")


def load_translations():
    path = os.path.join(HERE, "translations.json")
    if not os.path.exists(path):
        sys.exit(f"找不到翻译表：{path}")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("translations", {})


def plugin_root():
    root = os.environ.get("DECKY_PLUGIN_ROOT", DEFAULT_ROOT)
    if not os.path.isdir(root):
        sys.exit(f"找不到插件目录：{root}\n可用 DECKY_PLUGIN_ROOT 环境变量指定")
    return root


def split_manifest(src):
    """把 manifest 块从源码里切出来，返回 (剩余部分, manifest 原文或 None)"""
    m = MANIFEST_RE.search(src[:8000])
    if not m:
        return src, None
    return src[:m.start()] + "\x00MANIFEST\x00" + src[m.end():], m.group(0)


def patch_text(root, translations):
    """替换 dist/index.js 里的界面文案（manifest 块受保护）"""
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

        body, manifest = split_manifest(src)
        out = body
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

        if manifest is not None:
            out = out.replace("\x00MANIFEST\x00", manifest, 1)

        if out.count('"') != src.count('"'):
            print(f"  ! {folder}：引号数量异常，放弃写入")
            continue

        with open(js, "w", encoding="utf-8", errors="surrogateescape") as f:
            f.write(out)
        print(f"  ✓ {folder}：替换 {hits} 处")
        changed += hits
    print(f"文案替换合计 {changed} 处")


def restore(root, translations):
    for folder in translations:
        for rel in ("dist/index.js", "plugin.json"):
            target = os.path.join(root, folder, rel)
            bak = target + BACKUP_SUFFIX
            if os.path.exists(bak):
                shutil.copy2(bak, target)
                print(f"  ✓ {folder}/{rel} 已还原")


def doctor(root):
    """检查 plugin.json 的 name 与前端 manifest.name 是否一致，不一致则修复"""
    print("体检：plugin.json name ⟷ dist/index.js manifest.name\n")
    bad = 0
    for folder in sorted(os.listdir(root)):
        d = os.path.join(root, folder)
        pj = os.path.join(d, "plugin.json")
        js = os.path.join(d, "dist", "index.js")
        if not (os.path.exists(pj) and os.path.exists(js)):
            continue
        try:
            pname = json.load(open(pj, encoding="utf-8")).get("name")
        except Exception as e:
            print(f"  ! {folder}：plugin.json 解析失败 {e}")
            continue

        src = open(js, encoding="utf-8", errors="ignore").read()
        m = MANIFEST_RE.search(src[:8000])
        if not m:
            print(f"  - {folder:<26} 旧式打包，无 manifest")
            continue
        try:
            obj = json.loads(m.group(1))
        except Exception as e:
            print(f"  ! {folder}：manifest 解析失败 {e}")
            continue

        if obj.get("name") == pname:
            print(f"  OK {folder:<26} {pname}")
            continue

        old = obj.get("name")
        obj["name"] = pname
        block = "const manifest = " + json.dumps(
            obj, ensure_ascii=False, separators=(",", ":")
        ) + ";"
        src = src[:m.start()] + block + src[m.end():]
        with open(js, "w", encoding="utf-8") as f:
            f.write(src)
        print(f"  修 {folder:<26} manifest {old!r} → {pname!r}")
        bad += 1

    print()
    print(f"修复 {bad} 个" if bad else "全部一致，无需修复")
    if bad:
        print("请重启 Decky：sudo systemctl restart plugin_loader")


def status(root, translations):
    print(f"插件目录：{root}\n")
    rows = []
    for folder in sorted(translations):
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
    print(f"{'插件目录':<26}{'显示名':<18}{'中文字符':>8}   {'状态'}")
    print("-" * 66)
    for folder, name, zh, backup in rows:
        print(f"{folder:<26}{name:<18}{zh:>8}   {backup}")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "status"
    if mode not in ("apply", "restore", "doctor", "status"):
        sys.exit(__doc__)

    translations = load_translations()
    root = plugin_root()

    if mode == "status":
        status(root, translations)
        return

    if os.geteuid() != 0:
        sys.exit("需要 root 权限：sudo python3 zh_patch.py " + mode)

    if mode == "apply":
        print("汉化插件文案：")
        patch_text(root, translations)
    elif mode == "restore":
        print("还原英文：")
        restore(root, translations)
    elif mode == "doctor":
        doctor(root)
        return

    print("\n完成。重启 Decky 生效：sudo systemctl restart plugin_loader")


if __name__ == "__main__":
    main()
