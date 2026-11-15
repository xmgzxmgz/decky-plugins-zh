# Decky 插件汉化补丁

给 **Steam Deck（SteamOS）** 上的 [Decky Loader](https://github.com/SteamDeckHomebrew/decky-loader) 插件加上中文界面。

Decky 商店里的插件绝大多数只有英文，少数内置多语言（德语/西语/法语…）却唯独没有中文。这个补丁把常用插件的界面文案和插件名替换成简体中文，**全部改动可一键回滚**。

## 支持情况

| 插件（目录名） | 汉化条目 | 显示名 |
|---|---|---|
| `SDH-CssLoader` | 102 | 主题美化 |
| `PowerTools` | 76 | 性能调控 |
| `hltb-for-deck` | 18 | 通关时长 |
| `decky-steamgriddb` | 18 | 影音封面 |
| `protondb-decky` | 16 | 兼容性徽章 |
| `decky-storage-cleaner` | 14 | 存储清理 |
| `Decky-Undervolt` | 14 | 降压调校 |
| `moondeck` | 8 | 游戏串流 |
| `playcount-decky` | 6 | 在线人数 |
| `Bluetooth` | — | 蓝牙 |
| `DeckyClash` | — | 代理加速 |

合计 **272 条文案 + 10 个插件显示名**。

## 用法

把 `zh_patch.py` 和 `translations.json` 放到同一个目录（例如 `/home/deck/decky-zh/`），然后：

```bash
# 查看当前汉化状态（不需要 root）
python3 zh_patch.py status

# 汉化：内部文案 + 插件显示名
sudo python3 zh_patch.py apply

# 只汉化内部文案 / 只改显示名
sudo python3 zh_patch.py text
sudo python3 zh_patch.py names

# 全部还原英文
sudo python3 zh_patch.py restore
```

改完重启 Decky 生效：

```bash
sudo systemctl restart plugin_loader
```

插件目录不是默认路径时，可用环境变量指定：

```bash
sudo DECKY_PLUGIN_ROOT=/path/to/plugins python3 zh_patch.py apply
```

## 原理

Decky 插件的前端是一个打包好的 `dist/index.js`。绝大多数插件把英文串**同时当作 i18n 的 key 和显示值**：

```js
tr("Charge Limit")   // 查表 key
{ "Charge Limit": "Charge Limit" }   // 表里的英文值
```

所以把带引号的英文字面量**整体替换**成中文后，查表与显示会同步变化，逻辑不受影响：

```js
tr("充电上限")
{ "充电上限": "充电上限" }
```

字体由 Steam 自带的 Noto Sans CJK 提供，中文能正常显示。

## 安全设计

| 措施 | 说明 |
|---|---|
| 自动备份 | 修改前把原文件存为 `*.zhbak`，`restore` 从备份还原 |
| 引号校验 | 写入前比对双引号数量，与原文不一致就放弃写入，避免破坏 JS |
| 不翻状态值 | `Disabled` / `Enabled` / `Offline` / `Scheduled` 等既用于显示也用于逻辑判断，翻译会让状态错乱，一律跳过 |
| 不翻代码标识 | CSS 属性（`flex`/`strokeWidth`）、SVG 路径（`M0 0h24v24H0z`）、内部接口名（`GENERAL_load_settings`）全部跳过 |
| 改显示名是安全的 | Decky 的 `homebrew/settings/<目录>` 用的是**文件夹名**而非 `plugin.json` 的 `name`，因此改显示名不会丢插件配置 |

## 已知限制

- **插件更新会覆盖汉化**。Decky 装新版插件时会覆盖 `dist/index.js`，更新后重新跑一次 `apply` 即可（脚本会从备份或当前文件重新套用）。
- 只覆盖**界面文案**。插件通过 Python 后端返回的动态内容（如 Theme 名称、游戏名、服务器状态）不在范围内。
- 少数 UI 文案硬编码在图标按钮的 `title` 属性或图标组件里，未逐条处理。
- 插件名改成中文后，与 Decky 商店里的英文名不再对应，属预期行为。

## 贡献

翻译表在 `translations.json`，结构很简单：

```json
{
  "plugin_names": { "SDH-CssLoader": "主题美化" },
  "translations": {
    "SDH-CssLoader": { "Last Updated": "最后更新" }
  }
}
```

新增插件只需加一个 key（插件目录名）+ 对应英文原文。改完跑 `apply` 验证，`status` 里中文字符数会增加。

提取待翻译文案可以这样找：

```bash
grep -oE '"[A-Z][A-Za-z][A-Za-z0-9 ,.:%/()&+_-]{3,50}"' \
  /home/deck/homebrew/plugins/<插件目录>/dist/index.js | sort -u
```

## 免责声明

- 本项目只包含**界面文案翻译**，不包含任何插件源码或二进制文件。
- 插件版权归各自作者所有，本项目与 Valve、Decky Loader 及各插件作者均无关联。
- 修改插件文件属于非官方行为。脚本已尽量保守（备份 + 校验 + 可回滚），但仍建议**先备份重要配置**，出现问题用 `restore` 还原。
- 使用风险自负。

## License

MIT
