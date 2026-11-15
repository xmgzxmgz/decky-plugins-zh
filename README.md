# Decky 插件汉化补丁

给 **Steam Deck（SteamOS）** 上的 [Decky Loader](https://github.com/SteamDeckHomebrew/decky-loader) 插件加上中文界面。

Decky 商店里的插件绝大多数只有英文，少数内置多语言（德语/西语/法语…）却唯独没有中文。这个补丁把常用插件的界面文案替换成简体中文，**全部改动可一键回滚**。

## ⚠️ 千万不要修改插件的 `name`

这是本项目最重要的一条经验，写在这里是为了让你别踩。

Decky 的 IPC（前端调后端）**以 `plugin.json` 的 `name` 作为路由键**，而插件前端在打包时已经把名字写死在了 `dist/index.js` 里：

```js
const manifest = {"name":"Decky Clash"};        // 打包时固化，不会跟着 plugin.json 变
const internalAPIConnection = window.__DECKY_SECRET_..._deckyLoaderAPIInit;
if (!internalAPIConnection) throw new Error('[@decky/api]: Failed to connect to the loader...');
```

一旦你把 `plugin.json` 的 `name` 改成「代理加速」，后端就以「代理加速」注册，而前端还在找 `Decky Clash` —— **所有后端调用都路由不到，Promise 永久挂起**。

症状很有迷惑性：

| 现象 | 真实情况 |
|---|---|
| 插件面板一直显示「加载中…」 | 前端在等一个永远不返回的调用 |
| 点开关没反应，卡在加载中 | `set_core_status` 之类的调用发不出去 |
| 退出面板再进来显示「已关闭」 | 前端回落到 `localStorage` 里的旧状态 |
| 但代理/内核其实在正常工作 | 后端根本没有参与，是内核自己在跑 |
| 「版本」等字段一片空白 | 所有来自后端的数据都是空的 |

**本项目的 `apply` 不会碰 `name`**，也不会碰 `manifest`。如果你手动改过，或者用了别的脚本，用这个命令体检并自动修复：

```bash
sudo python3 zh_patch.py doctor
sudo systemctl restart plugin_loader
```

## 支持情况

| 插件（目录名） | 汉化条目 |
|---|---|
| `SDH-CssLoader` | 102 |
| `PowerTools` | 76 |
| `DeckyClash` | 30 |
| `hltb-for-deck` | 18 |
| `decky-steamgriddb` | 18 |
| `protondb-decky` | 16 |
| `decky-storage-cleaner` | 14 |
| `Decky-Undervolt` | 14 |
| `moondeck` | 8 |
| `playcount-decky` | 6 |

合计 **302 条文案**，覆盖 10 个插件。

> Decky 面板首屏显示的是插件**名字**，那些是各插件作者定的，本项目不改（原因见上）。改的是进入插件之后的界面文案。

## 用法

把 `zh_patch.py` 和 `translations.json` 放到同一个目录（例如 `/home/deck/decky-zh/`），然后：

```bash
# 查看当前汉化状态（不需要 root）
python3 zh_patch.py status

# 汉化
sudo python3 zh_patch.py apply

# 还原英文
sudo python3 zh_patch.py restore

# 体检：检查 plugin.json 与前端 manifest 的插件名是否错位
sudo python3 zh_patch.py doctor
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
| manifest 保护 | `const manifest = {...}` 整块被切出来单独保存，文案替换不会碰到它 |
| 不碰 `name` | 从不修改 `plugin.json`，从根上避免 IPC 断裂 |
| 不翻状态值 | `Disabled` / `Enabled` / `Offline` / `Scheduled` 等既用于显示也用于逻辑判断，翻译会让状态错乱，一律跳过 |
| 不翻代码标识 | CSS 属性（`flex`/`strokeWidth`）、SVG 路径（`M0 0h24v24H0z`）、内部接口名（`GENERAL_load_settings`）全部跳过 |

## 已知限制

- **插件更新会覆盖汉化**。Decky 装新版插件时会覆盖 `dist/index.js`，更新后重新跑一次 `apply` 即可。注意 `*.zhbak` 是首次汉化时的原始英文，插件升级后它还是旧版，`apply` 会以旧版为基准替换 —— 若新版文案有变动，建议先删掉 `*.zhbak` 再用 `apply` 重新建立基准。
- 只覆盖**界面文案**。插件通过 Python 后端返回的动态内容（如 Theme 名称、游戏名、服务器状态）不在范围内。
- 少数 UI 文案硬编码在图标按钮的 `title` 属性或图标组件里，未逐条处理。
- `PowerTools` / `SDH-CssLoader` 是旧式 UMD 打包，不使用 `const manifest`，`doctor` 会跳过它们（正常现象）。

## 贡献

翻译表在 `translations.json`，结构很简单：

```json
{
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

**提交 PR 时请只加文案，不要加插件改名。**

## 免责声明

- 本项目只包含**界面文案翻译**，不包含任何插件源码或二进制文件。
- 插件版权归各自作者所有，本项目与 Valve、Decky Loader 及各插件作者均无关联。
- 修改插件文件属于非官方行为。脚本已尽量保守（备份 + 校验 + 可回滚），但仍建议**先备份重要配置**，出现问题用 `restore` 还原。
- 使用风险自负。

## License

MIT
