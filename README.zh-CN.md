<div align="right"><a href="README.md">English</a></div>

<p align="center"><img src="docs/hero.png" alt="CE Agent CLI —— 以 AI agent 友好的 CLI 提供 Cheat Engine 风格的进程内存分析" width="100%"></p>

CE Agent CLI（`cli-anything-cheatengine`）将 Cheat Engine 的核心工作流 —— 进程附加、带类型的内存读写、数值扫描、cheat table（`.CT`）增删改查、汇编/反汇编，以及符号解析 —— 重新实现为一个 Windows 命令行工具。每条命令都遵循为 AI agent 设计的 `--json` 契约；当有正在运行的 Cheat Engine 7.x 实例时，一个可选的命名管道桥接可驱动该实例（speedhack、调试器、auto-assemble、PDB 符号）。它面向本地调试、安全研究与进程自省而构建。

> **仅限授权使用。** 只附加并分析你本人拥有、或已获得明确书面许可可以检查的进程。本工具用于本地调试、安全研究与进程自省 —— 不得用于违反任何软件的服务条款或反作弊保护，也不得用于违反任何适用法律。

## ✨ 亮点特性

- **广泛的命令面** —— 8 个命令组、约 30 个子命令，覆盖附加、内存、扫描、`.CT` 表、汇编与符号。
- **agent 友好的 `--json` 契约** —— 每条命令都提供全局 `--json` 模式以输出结构化结果，并附带 `SKILL.md` 描述文件，便于 agent 发现其能力。
- **98 项测试，无需管理员权限或目标进程** —— 79 项核心测试 + 19 项 CLI 测试，全部无需管理员权限或运行中的目标进程即可执行。
- **带类型的内存读写** —— 对进程内存提供带类型的读取器与写入器；数值扫描仅遍历已提交（committed）的内存区域。
- **符号解析** —— 从 PE 导出表解析符号，并可通过 Cheat Engine 桥接获得可选的 PDB 符号。
- **可选的汇编/反汇编** —— 安装 `[asm]` 附加项后，由 Capstone 与 Keystone 提供反汇编与汇编能力。
- **Cheat Engine 7.x 桥接** —— 通过命名管道驱动 speedhack、调试器与 auto-assemble；当 CE 未运行时优雅降级。

## 🏗 架构

<p align="center"><img src="docs/architecture.png" alt="CE Agent CLI 架构：命令组之上的 CLI、基于 ctypes 的内核，以及可选的 Cheat Engine 桥接" width="100%"></p>
<p align="center"><sub>一个直接架在 Windows API 之上的自足内核，外加一条通往运行中 Cheat Engine 7.x 的可选桥接。</sub></p>

CLI 就是全部对外表面：八个命令组 —— `process`、`memory`、`scan`、`table`、`asm`、`symbol`、`session` 与 `bridge` —— 架在一个内核之上，由该内核完成进程附加、带类型的内存读写、在已提交（committed）区域上的数值扫描、`.CT` cheat table 增删改查、汇编与反汇编，以及符号解析。这个内核通过 `ctypes` 直接与 Windows 对话，中间不经过 `pywin32`；这也正是独立工具本身并不依赖 Cheat Engine 的原因。

图中的虚线路径是可选的另一半。当有 Cheat Engine 7.x 实例在运行时，CLI 会通过命名管道与其连接，从而获得 speedhack、调试器、auto-assemble 与 PDB 符号；当其未运行时，这些功能会优雅降级，内核中的一切仍可继续工作。贯穿两半的是全局 `--json` 开关：任何命令都可以输出结构化结果而非人类可读文本 —— 它与随附的 `SKILL.md` 描述文件一起，构成了 AI agent 驱动本工具所依赖的契约。

## 🧰 技术栈

| 领域 | 说明 |
| --- | --- |
| 语言 | Python ≥ 3.9 |
| 系统接口 | 通过 `ctypes` 调用 Windows API（不使用 `pywin32`） |
| CLI 与进程 | `click`、`psutil` |
| 可选 `[asm]` 附加项 | `keystone-engine`、`capstone` |
| 桥接 | 通过命名管道连接 Cheat Engine 7.x（可选） |

## 🚀 快速开始

前置条件：Windows、Python 3.9+，以及执行实时内存操作所需的管理员权限。Cheat Engine 7.x 为可选，仅在使用桥接时需要。

```bash
# 安装（核心）
pip install -e .

# 或安装带汇编/反汇编支持的版本
pip install -e ".[asm]"

# 以 JSON 形式列出进程
cli-anything-cheatengine --json process list
```

## 🧪 测试

```bash
pytest
```

98 项测试（79 项核心 + 19 项 CLI）无需管理员权限或运行中的目标进程即可执行。

## 📄 许可证

MIT —— 见 [LICENSE](LICENSE) 文件。

<p align="center"><sub>由 <a href="https://github.com/SensLiao">Ruixuan "Sens" Liao</a> 构建 · USYD Advanced Computing (Honours)</sub></p>
