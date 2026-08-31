<div align="right"><a href="README.md">English</a></div>

<p align="center"><img src="docs/hero.png" alt="CE Agent CLI — 以 AI 代理就绪的 CLI 形式重做 Cheat Engine 式进程内存分析" width="100%"></p>

<p align="center">
  <img src="https://img.shields.io/badge/platform-Windows-dc2626?style=flat" alt="平台：Windows">
  <img src="https://img.shields.io/badge/Python-%E2%89%A5%203.9-dc2626?style=flat" alt="Python 3.9 及以上">
  <img src="https://img.shields.io/badge/interface-CLI%20%C2%B7%20--json-dc2626?style=flat" alt="带 --json 契约的 CLI">
  <img src="https://img.shields.io/badge/tests-98%20passing-2f9e44?style=flat" alt="98 个测试通过">
  <img src="https://img.shields.io/badge/license-MIT-2f9e44?style=flat" alt="许可证：MIT">
</p>

CE Agent CLI（`cli-anything-cheatengine`）把 Cheat Engine 的核心工作流——进程附加、带类型的内存读写、数值扫描、作弊表（`.CT`）编辑、汇编/反汇编、符号解析——重做成一个 Windows 命令行工具，其中**每一条命令都提供为 AI 代理设计的 `--json` 契约**。当有 Cheat Engine 7.x 在运行时，可选的命名管道桥接会补上变速、调试器、auto-assemble 与 PDB 符号；没有它时，独立内核照常工作。本工具面向本地调试、安全研究与进程内省。

> [!WARNING]
> **仅限授权使用。** 只附加与分析你自己拥有、或已获得明确书面许可检查的进程。不要用本工具绕过反作弊、DRM 或授权机制，不要篡改网络或多人游戏，也不要违反任何软件的服务条款或适用法律。详见 [`SECURITY.md`](SECURITY.md)。

<p align="center">
  <a href="#-快速开始">快速开始</a> ·
  <a href="#-常见工作流">常见工作流</a> ·
  <a href="#-命令参考">命令参考</a> ·
  <a href="#-json-契约">JSON 契约</a> ·
  <a href="#-cheat-engine-桥接">CE 桥接</a>
</p>

## 🧭 概览

**问题。** Cheat Engine 是为人手点击对话框而生的 GUI。这让它的能力——扫描、带类型的内存编辑、作弊表、反汇编——几乎无法被脚本或 AI 代理使用：后者需要的是结构化输入与结构化输出，而不是一个可以点的窗口。

**方案。** 本工具把那套工作流重建为可组合的 CLI。它通过 `ctypes` 直接与 Windows 对话（中间没有 `pywin32`），因此独立内核完全不依赖 Cheat Engine；一个全局 `--json` 开关把每条命令的输出变成代理可解析的结构化信封。随包提供的 `SKILL.md` 描述符让 AI 代理能够发现能力面并驱动它。而在运行中的 Cheat Engine 7.x 确实能带来价值的地方——变速、真正的调试器、auto-assemble、PDB 符号——一条可选的命名管道桥接会伸进去取用，CE 不在时优雅降级。

**范围。** 仅限 Windows，且本质上是双用途工具：它读写另一个进程的内存空间，并能驱动调试器。它面向获得授权的本地调试、安全研究与进程内省，[`SECURITY.md`](SECURITY.md) 对此有明确表述。它不是修改器、不是反作弊绕过工具，也不包含任何游戏专用内容。98 个测试在无管理员权限、无活动目标进程的条件下运行。

## ✨ 亮点

- **宽广的命令面** — **8 个命令组、42 个子命令**，覆盖进程附加、带类型内存、扫描、`.CT` 表、汇编、符号、会话状态与 CE 桥接。
- **每条命令都有面向代理的 `--json` 契约** — 全局 `--json` 输出结构化信封，随包的 `SKILL.md` 描述符让代理能发现并驱动整个命令面。
- **独立内核，不需要 Cheat Engine** — 进程操作经 `ctypes` 直达 Windows API（无 `pywin32`），只装 Python 即可运行内核。
- **带撤销的类型化内存读写** — 7 种值类型（`byte` 到 `double`，外加 `string`）；每次写入都记录撤销条目，`session undo` / `redo` 可还原保存的字节。
- **在已提交内存上的数值扫描** — 首次与后续扫描支持 8 种 Cheat Engine 扫描模式（`exact`、`between`、`bigger`、`smaller`、`increased`、`decreased`、`changed`、`unchanged`），作用于 6 种数值类型。
- **真正可用的 `.CT` 作弊表编辑** — 用标准库 XML 解析实现加载、保存、列出、新增、删除、冻结与解冻：不需要 CE，也不需要管理员权限。
- **可选的汇编/反汇编** — 安装 `[asm]` 附加依赖后，由 Capstone 与 Keystone 驱动 `asm` 命令组。
- **Cheat Engine 7.x 桥接** — 一条命名管道链路带来变速、调试器、auto-assemble 与支持 PDB 的符号解析，CE 未运行时优雅降级。
- **98 个测试，不需要管理员权限也不需要目标进程** — 79 个内核测试加 19 个 CLI 测试。

## 🏗 架构

<p align="center"><img src="docs/architecture.png" alt="CE Agent CLI 架构：8 个 CLI 命令组位于 ctypes 内核之上，外加通往 Cheat Engine 的可选命名管道桥接" width="100%"></p>
<p align="center"><sub>Windows API 之上的自包含内核，加一条通往运行中 Cheat Engine 7.x 的可选桥接。</sub></p>

CLI 就是全部对外表面。8 个命令组坐落在一个**内核**之上，内核负责进程附加、带类型的内存读写、在已提交区域上的数值扫描、`.CT` 作弊表增删改查、汇编与反汇编、符号解析——而该内核通过 `ctypes` 直接与 Windows 对话，这正是独立工具完全不需要 Cheat Engine 的原因。

图中的虚线路径是可选的另一半。当有 Cheat Engine 7.x 在运行时，CLI 提供一条命名管道由 CE 反向连入，从而获得变速、调试器、auto-assemble 与 PDB 符号；CE 不在时，这些命令会如实说明，内核的一切照常工作。横贯两半的是全局 `--json` 开关：任何命令都能输出结构化信封而非给人看的文本——这正是 AI 代理驱动本工具所依据的契约。

## 🚀 快速开始

### 环境要求

- **Windows**，**Python 3.9+**
- 实时内存操作（附加、读写、扫描、反汇编）需要**管理员权限**——文件与表操作则不需要
- 可选：用于汇编/反汇编的 `[asm]` 附加依赖，以及用于桥接的 **Cheat Engine 7.x**

### 安装

```bash
pip install -e .
```

<details>
<summary>需要汇编/反汇编支持时</summary>

```bash
pip install -e ".[asm]"
```

这会引入 `keystone-engine` 与 `capstone`。不装则 `asm` 命令组不可用，其余一切正常。

</details>

### 运行第一条命令

```bash
cli-anything-cheatengine --json process list -n notepad
```

### 预期输出

一个结构化信封——这条命令不需要管理员权限：

```json
{
  "success": true,
  "count": 1,
  "processes": [
    {
      "pid": 12345,
      "name": "notepad.exe",
      "exe": "C:\Windows\System32\notepad.exe",
      "username": "DESKTOP\you",
      "memory_mb": 24.3,
      "status": "running"
    }
  ]
}
```

失败也是同样的形状——`{"success": false, "error": "..."}`——而且**退出码仍然是 0**，所以请根据 `success` 字段分支，而不是退出码。没有管理员权限时，任何需要附加进程的命令都会返回清晰的权限错误，而不是悄悄失败；见[权限矩阵](#-权限矩阵)。

## 📖 常见工作流

### 在运行中的进程里找到一个数值并冻结它

```bash
cli-anything-cheatengine process list -n game          # 找到 PID
cli-anything-cheatengine process attach 1234           # 附加（需管理员）
cli-anything-cheatengine scan first 100 -t dword       # 首次扫描 100
cli-anything-cheatengine scan next 95 -m exact         # 数值变成了 95
cli-anything-cheatengine scan results --limit 10       # 查看幸存结果
cli-anything-cheatengine memory write 0x1A2B3C 999 -t dword
cli-anything-cheatengine table add-entry table.CT -d "Health" -a 0x1A2B3C -t dword --frozen
```

### 不知道具体数值时逐步收窄

```bash
cli-anything-cheatengine scan first 0 -t float -m bigger
cli-anything-cheatengine scan next -m decreased        # 数值下降之后
cli-anything-cheatengine scan next -m unchanged        # 数值保持不变之后
cli-anything-cheatengine scan reset                    # 重新开始
```

`scan next` 支持 8 种模式：`exact`、`between`、`bigger`、`smaller`、`increased`、`decreased`、`changed`、`unchanged`。

### 不开进程、不用管理员权限编辑作弊表

```bash
cli-anything-cheatengine table list-entries table.CT
cli-anything-cheatengine table add-entry table.CT -d "Ammo" -a "game.exe+0x4C210" -t dword
cli-anything-cheatengine table freeze table.CT 3
cli-anything-cheatengine table save table.CT -o table-edited.CT
```

`.CT` 文件用标准库 XML 解析器读写。Cheat Engine 存储的、超出本工具处理的六个字段之外的内容（auto-assemble 脚本、偏移、快捷键、Lua）在保存时不会保留，因此请在副本上操作。

### 撤销一次内存写入

```bash
cli-anything-cheatengine session status     # 当前附加对象、扫描与撤销深度
cli-anything-cheatengine session undo       # 还原之前的字节
cli-anything-cheatengine session redo
```

### 解析符号并在其附近反汇编

```bash
cli-anything-cheatengine symbol list-modules              # 不需要管理员权限
cli-anything-cheatengine symbol lookup "game.exe+0x4C210" # 需管理员
cli-anything-cheatengine asm disassemble 0x7FF6A2B10000 -c 20
```

### 驱动 Cheat Engine 使用高级功能

```bash
cli-anything-cheatengine bridge detect        # CE 7.x 在运行吗？
cli-anything-cheatengine bridge start         # 提供管道，并打印 .lua 路径
cli-anything-cheatengine bridge speed set 3.0
cli-anything-cheatengine bridge debug break 0x7FF6A2B10000
cli-anything-cheatengine bridge aa trainer.asm
cli-anything-cheatengine bridge stop
```

## 🧾 命令参考

8 个组、42 个子命令。`--json` 是全局开关；实时内存类命令需要管理员权限（见[权限矩阵](#-权限矩阵)）。

| 组 | 子命令 | 作用 |
| --- | --- | --- |
| **process** | `list` · `attach` · `detach` · `info` | 查找、附加与检查进程（`list` 与 `info` 不需管理员）。 |
| **memory** | `read` · `write` · `dump` | 按地址做带类型读写，以及十六进制转储。每次写入可撤销。 |
| **scan** | `first` · `next` · `results` · `reset` | 发起扫描、逐步收窄、翻页查看结果、重置。 |
| **table** | `load` · `save` · `list-entries` · `add-entry` · `remove-entry` · `freeze` · `unfreeze` | 完整的 `.CT` 作弊表编辑——纯 XML，不需要 CE，不需要管理员。 |
| **asm** | `assemble` · `disassemble` · `inject` | 汇编与反汇编 x86/x64（`[asm]` 附加依赖）；对活动进程反汇编与注入。 |
| **symbol** | `lookup` · `list-modules` | 解析 `module+offset` 与 PE 导出；列出已加载模块。 |
| **session** | `status` · `history` · `undo` · `redo` · `reset` | 查看与管理持久化会话状态；撤销与重做内存写入。 |
| **bridge** | `detect` · `start` · `status` · `lua` · `stop` · `aa` · `resolve` · `speed {set,reset}` · `debug {break,remove,continue}` · `ct {activate,deactivate}` | 驱动运行中的 Cheat Engine 7.x。 |

**值类型**（`-t`）：`byte`、`word`、`dword`、`qword`、`float`、`double`、`string`。其中 6 种数值类型可扫描；字符串与字节数组可读写但不可扫描。

## 🔌 JSON 契约

每条命令都接受全局 `--json`，输出一个扁平信封：成功时把 `"success": true` 与命令自身的键合并，失败时是 `{"success": false, "error": "<message>"}`。错误情况下**退出码仍为 0**——**代理应当根据 `success` 字段分支，而不是退出码。**

```json
{ "success": true, "address": "0x1A2B3C", "type": "dword", "value": 100 }
```

```json
{ "success": true, "pid": 1234, "name": "game.exe", "handle": "0x2f0", "is_64bit": true }
```

```json
{ "success": true, "var_type": "dword", "result_count": 128,
  "scan_count": 2, "last_scan_option": "EXACT_VALUE", "elapsed_ms": 412 }
```

```json
{ "success": true, "total": 128, "offset": 0, "limit": 2,
  "results": [ { "address": "0x1A2B3C", "value": 95, "previous_value": 100 } ] }
```

## 🔗 Cheat Engine 桥接

桥接完全可选——内核不需要 Cheat Engine。确实要用高级功能时，由 CLI 运行命名管道**服务端**，Cheat Engine 作为客户端连入：

1. `bridge detect` — 确认 CE 7.x 正在运行（无需连接）。
2. `bridge start` — 启动管道服务端；它会打印 `ce_lua_client.lua` 的路径。
3. 在 Cheat Engine 中打开 **Lua Engine**（Ctrl+Alt+L），粘贴该文件内容，点击 **Execute**——CE 会连回来并报告自己的版本。
4. 此后 `bridge speed`、`bridge debug`、`bridge aa`、`bridge ct` 与 `bridge resolve`（支持 PDB）均可用；`bridge stop` 断开连接。

Lua 客户端随包提供（`bridge/ce_lua_client.lua`），但需要手工粘贴——它不是 CE 插件，也不是 `.CETRAINER`，不会向 Cheat Engine 自动安装任何东西。由于它未被声明为 package data，若打算使用桥接请以 `-e`（可编辑模式）安装。

## 🤖 从 AI 代理驱动

随包的 skill 描述符（[`cli_anything/cheat_engine/skills/SKILL.md`](cli_anything/cheat_engine/skills/SKILL.md)）正是让代理发现并操作本工具的东西。它声明了可执行文件名、9 个触发短语（`memory scan`、`cheat table`、`speedhack`、`auto assemble` 等），并把命令参考明确拆成*独立*与*桥接*两类，让代理知道哪些需要 CE 在运行。它还带有两条端到端工作流——独立模式的"查找并冻结"，以及 CE 高级会话——外加一条书面降级规则：使用任何桥接命令前先用 `bridge detect` 探测。配合 JSON 信封，代理在每一步都能拿到机器可读的输出。

## 🖥 权限矩阵

| 需要管理员权限 | 无需管理员权限 |
| --- | --- |
| `process attach`；全部 `memory` 命令；`scan first` 与 `scan next`；`asm disassemble` 与 `asm inject`；`symbol lookup`；`session undo` 与 `redo` | `process list` / `info` / `detach`；`scan results` / `reset`；全部 7 条 `table` 命令；`asm assemble`；`symbol list-modules`；`session status` / `history` / `reset`；`bridge detect` |

任何需要附加进程的操作都要求管理员权限，并会抛出清晰的权限错误，而不是悄无声息地失败。除 `detect` 外的桥接命令还额外要求一个正在运行且已连接的 Cheat Engine 7.x。

## 🗂 会话状态

会话状态持久化在 `~/.cli-anything/cheat-engine/sessions/current_session.json`：当前附加的进程、已加载的表、扫描标志与结果计数、内存写入的撤销/重做栈（最近 50 条）以及命令历史（最近 100 条）。新的写入会清空重做栈；文件损坏时回退为全新会话。扫描*结果*本身是进程局部的、有意不做持久化——跨调用只保留计数。

## 🖥 兼容性

| 组件 | 支持情况 |
| --- | --- |
| 操作系统 | 仅 Windows（`ctypes` 直连 kernel32；无 POSIX 路径） |
| Python | 3.9 及以上 |
| 目标架构 | 32 位与 64 位（附加时报告 `is_64bit`） |
| Cheat Engine | 7.x，可选——仅桥接需要 |
| 汇编 | 需要 `[asm]` 附加依赖（Keystone 与 Capstone） |
| 测试 | 在 Windows 上运行，无需管理员权限与活动目标 |

## 🧰 技术栈

| 领域 | 详情 |
| --- | --- |
| 语言 | Python 3.9+ |
| 系统接口 | 经 `ctypes` 调用 Windows API（无 `pywin32`） |
| CLI 与进程 | `click`、`psutil` |
| 可选 `[asm]` 附加依赖 | `keystone-engine`、`capstone` |
| `.CT` 解析 | `xml.etree.ElementTree`（标准库） |
| 桥接 | 经命名管道连接 Cheat Engine 7.x（可选） |
| 控制台入口 | `cli-anything-cheatengine` |

## 🧪 测试

```bash
pytest
```

**98 个测试（79 内核 + 19 CLI）** 在无管理员权限、无活动目标进程的条件下运行。CLI 测试通过 Click 的 `CliRunner` 覆盖 `table`、`session` 与 `--help`；`test_bridge.py` 在不需要 Cheat Engine 的情况下覆盖命名管道协议。

## 📊 项目状态

- **稳定** — 独立内核：process、memory、scan、table、symbol 与 session 命令组，均被测试套件覆盖。
- **可选扩展** — `asm` 组需要 `[asm]` 附加依赖；桥接需要运行中的 Cheat Engine 7.x 以及手工粘贴的 Lua 客户端。
- **有意为之** — 扫描结果只在单次 CLI 进程内存活；`.CT` 往返保留六个已处理字段、丢弃 CE 专有扩展；错误通过 JSON 信封而非退出码汇报。

## 🙋 获取帮助

- **用法与命令语法** — `cli-anything-cheatengine --help`，或任一命令组的 `--help`；[skill 描述符](cli_anything/cheat_engine/skills/SKILL.md) 本身就是一份完整命令参考。
- **可复现的 Bug** — 提交 GitHub issue，附上 Windows 版本、Python 版本、确切命令及其 `--json` 输出。
- **安全漏洞** — **不要**公开提 issue；按 [`SECURITY.md`](SECURITY.md) 的流程报告。

## 🔒 负责任使用

> 本工具面向**获得授权的**本地调试、安全研究与进程内省。只附加你自己拥有、或已获明确书面许可检查的进程。不要用它对付反作弊、DRM 或授权系统，不要用于网络或多人游戏，也不要违反任何服务条款或法律。实时内存操作按设计需要管理员权限，本地命名管道也只应在可信环境中启用。

## 📄 许可证

MIT — 见 [`LICENSE`](LICENSE)。

<p align="center"><sub>由 <a href="https://github.com/SensLiao">Ruixuan "Sens" Liao</a> 构建 · 悉尼大学 Advanced Computing（Honours）</sub></p>
