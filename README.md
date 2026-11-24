# EQ 切换器 v2.0 —— 交接文档（给负责 UI / 功能开发的 AI）

> 这是一个 Windows 小工具：在 **Equalizer APO** 上实时切换耳机 EQ 预设。
> 当前实现是 **Python 3 + tkinter** 单文件，无第三方依赖。
> 本文档描述：**它现在怎么工作、哪些地方可以重做、做的时候必须遵守什么约束**。

---

## 分析面板（2026-11-22 新增）

右侧实时显示当前生效预设的频率响应：

- 曲线：20 Hz – 20 kHz，按预设里的 Preamp / Filter 计算
- 峰值增益：曲线最大值，> 0 dB 时标红
- 滤波器数量、预增益
- 切换预设后自动刷新
- 预设列表超过可视高度时可滚动

说明：这是根据预设文本计算的近似曲线，不读取 APO 运行时状态；
GraphicEQ / Convolution 等复杂指令暂不纳入计算。


## 设备选择（2026-11-22 新增）

顶部「作用设备」下拉决定 EQ 只对哪个播放设备生效：

`
全部设备（不限定）   不写 Device 行，APO 对所有启用 APO 的设备生效（旧行为）
FiiO K11 · 扬声器     写 Device: FiiO K11 扬声器; {GUID}
`

- 点击「含未连接」可显示当前没插上的设备（例如暂时关闭的 K11）
- 选设备后切换预设，生成的 config.txt 会多一行 Device: <匹配串>; <GUID>
- 匹配串同时给名称和 GUID，名称对不上时 GUID 兜底
- 前提：目标设备本身要装过 Equalizer APO（否则 EQ 不会生效）
- 读取当前 config 的 Device 行，启动时会自动选中对应设备


## 1. 它解决什么问题

用户有多个 Equalizer APO 预设（不同耳机 / 不同用途：听歌、打游戏、夜间低音量、模拟老功放音色）。
过去切换要手动编辑 `config.txt`，很麻烦。
这个工具把"切换预设"变成**点一下按钮**，并显示当前生效的是哪个。

**典型使用场景**

| 场景 | 用哪个预设 |
|---|---|
| 日常听歌 | HD 490 Pro 实测校准（绒布耳罩） |
| 打无畏契约 | 打瓦专用（脚步强化） |
| 深夜小音量 | 夜间/低音量 |
| 想要"厚"的低频 | 厚声模拟 |
| 用另一副耳机 | DT 700 Pro X 听歌 |
| 不要任何 EQ | 关闭（bypass） |

---

## 2. 运行环境（硬约束）

| 项 | 值 |
|---|---|
| 操作系统 | **Windows 10 / 11（仅 Windows）** |
| Python | 3.12（当前用 `F:\ANACONDA\python.exe`，`pythonw.exe` 跑无控制台） |
| 依赖 | **仅标准库**：`tkinter`、`ctypes`、`os`、`shutil`、`time`、`sys` |
| 权限 | **必须管理员**（要写 `C:\Program Files\EqualizerAPO\config`） |
| 外部软件 | Equalizer APO 1.4.1（已装，挂在 FiiO K11 输出端点） |

**已安装路径（写死在上游不需要改，但请保留可配置性建议）**

```
预设源目录：F:\int\eq
APO 配置目录：C:\Program Files\EqualizerAPO\config
APO 主配置：  C:\Program Files\EqualizerAPO\config\config.txt
```

---

## 3. 数据模型（必须保持兼容）

### 3.1 预设文件

一个预设 = 一个 **纯文本文件**，扩展名 `.txt`，内容就是 Equalizer APO 的参数行：

```text
# 注释行（以 # 开头，允许中文）
Preamp: -5.5 dB
Filter 1: ON PK Fc 63 Hz Gain -1.2 dB Q 1.00
Filter 2: ON LSC Fc 105 Hz Gain 5.5 dB Q 0.71
Filter: ON HSC Fc 10000 Hz Gain -4.0 dB Q 0.71
```

**语法要点（来自 Equalizer APO）**

| 指令 | 格式 | 说明 |
|---|---|---|
| Preamp | `Preamp: -5.5 dB` | 增益补偿，防削波 |
| PK | `Filter: ON PK Fc <Hz> Gain <dB> Q <Q>` | 峰值滤波器 |
| LS / LSC | `Filter: ON LS Fc <Hz> Gain <dB> Q <Q>` | 低架（LSC 带 Q） |
| HS / HSC | `Filter: ON HS Fc <Hz> Gain <dB> Q <Q>` | 高架（HSC 带 Q） |
| 编号 | `Filter 1: ON ...` | 编号可选，用于 UI 排序 |

**编码：UTF-8（无 BOM 也可以，APO 能读；有中文注释时建议 UTF-8）**

### 3.2 当前生效状态的表达方式

**没有状态文件。** 当前生效的预设 = `config.txt` 里唯一一条未注释的 `Include:` 行：

```text
# 由 EQ 切换器生成 2026-11-22 04:12:33
# 当前配置: HD 490 Pro 实测校准（绒布耳罩）

Include: hd490pro-oratory-mix.txt
```

**旁路（关闭 EQ）= config.txt 里没有任何 Include 行**，例如：

```text
# EQ 已关闭（由切换器）

```

**重要：这行 Include 引用的文件必须已经复制到 APO 的 config 目录里**（同一个目录，相对文件名）。

---

## 4. 当前实现（v1）行为

```
┌───────────────────────────────┐
│ Equalizer APO 配置切换         │
│ 设备：FiiO K11                │
│ （非管理员时显示红色提示条）    │
│                               │
│ ● 490 Pro 实测校准（绒布耳罩）  │  ← 绿色圆点 = 当前生效
│   490 Pro 实测校准（厚布耳罩）  │
│   490 Pro 我调 · 补低频+人声    │
│   490 Pro 夜间/低音量          │
│   490 Pro 厚声模拟（老功放味）  │
│   490 Pro 打瓦 HRTF（通用）    │
│   490 Pro 打瓦专用（脚步强化）  │
│   DT 700 Pro X 听歌            │
│                               │
│ 当前生效：490 Pro 实测校准       │
│                               │
│ [刷新列表] [关闭 EQ] [以管理员重启]│
└───────────────────────────────┘
```

**已实现功能**

| 功能 | 实现方式 |
|---|---|
| 自动发现预设 | 扫描 `F:\int\eq\*.txt`，按内置名称表排序 |
| 显示当前生效 | 解析 `config.txt` 的 `Include:` |
| 点击切换 | 复制预设到 APO 目录 → 备份旧 config → 重写 config |
| 关闭 EQ | 重写 config 为只有注释 |
| 自动备份 | 每次写之前 `config.bak-yyyyMMdd-HHmmss.txt` |
| 自动提权 | 外层 `.cmd` 用 `net session` 检测 → `Start-Process -Verb RunAs` 重启自身 |
| 非管理员降级 | 只读模式，红字提示 + "以管理员重启"按钮 |

**关键代码位置（`eq-switcher.py`）**

| 函数 | 职责 |
|---|---|
| `is_admin()` | 判断是否管理员 |
| `relaunch_as_admin()` | `ShellExecuteW(None,"runas",...)` 重启自身 |
| `discover()` | 扫目录、按 NAME_MAP 排序 |
| `App.read_active()` | 解析 config.txt 的 Include |
| `App.apply(fn)` | 复制 + 备份 + 重写 config |
| `App.bypass()` | 清空 config 的 Include |
| `App.build()` | 重建按钮列表 + 高亮 |

---

## 5. 必须遵守的规则（改动时不要破坏）

1. **写 config.txt 前必须备份**（`config.bak-<时间戳>.txt`）。
2. **只改 config.txt，不改预设文件**（除非用户明确要求编辑）。
3. **复制预设到 APO 目录**后才能被 Include 引用。
4. **保持只写 `Include:` 一行**，不要生成多个 Include（APO 会叠加，容易削波）。
5. **不要动 `config.txt` 之外的文件**（`dt700.txt` 等是预设，不是配置）。
6. **UI 必须能显示"当前生效"**，否则用户不知道状态。
7. **非管理员时不要静默失败**，要明确提示并提供提权入口。

---

## 6. 已知限制 / 可改进方向（这是留给你的任务清单）

### 6.1 UI 层面

| 现状 | 建议 |
|---|---|
| tkinter 原生控件，简陋 | 换成 **PySide6 / PyQt6 / CustomTkinter / Flet / Web（Tauri/localhost）** |
| 无图标、无主题 | 加暗色主题、预设图标、耳机/音箱图标 |
| 列表式按钮 | 改成**卡片网格**（显示预设名 + 用途标签 + 迷你频响曲线） |
| 无频响可视化 | 解析 Filter 行，**画出 EQ 曲线**（RBJ biquad 幅频响应） |
| 无拖动排序 | 支持用户自定义顺序/分组 |

### 6.2 功能层面

| 现状 | 建议 |
|---|---|
| 手动切换 | **监听进程自动切换**（检测 `VALORANT-Win64-Shipping.exe` → 自动打瓦预设，退出 → 恢复） |
| 无热键 | 加 **全局 A/B 热键**（Ctrl+Alt+B 对比 EQ 开/关） |
| 无托盘 | 最小化到**系统托盘**（pystray） |
| 无导入 | 支持导入 **AutoEQ / oratory1990 的 ParametricEQ.txt**（解析 `Filter N:` 行） |
| 无编辑 | 内置**参数编辑**（改 Gain/Fc/Q，实时预览曲线） |
| 无预设管理 | 新建/删除/重命名/导入/导出预设 |
| 只支持一个设备 | 支持**多输出设备**（K11 / 小尾巴 / 显示器音频分别配置） |
| 无响度保护 | 自动计算**峰值增益**，自动设 Preamp（防削波） |

### 6.3 工程层面

| 现状 | 建议 |
|---|---|
| 路径写死 `F:\int\eq` | 用 `%APPDATA%` 或配置文件存路径 |
| 名称表写死在代码 | 移到 `presets.json`（名称、标签、描述、排序、适用耳机） |
| 单文件 7KB | 拆成 `ui.py` / `apo_backend.py` / `presets.py` |
| 无测试 | 加单元测试（config 读写、Include 解析、备份命名） |
| 无日志 | 加日志文件（便于排查"切换无效"） |
| 仅 Windows | 保持 Windows（APO 本身就只在 Windows） |

---

## 7. 一个参考实现：Equalizer APO 的接口细节

**不需要调用 APO 的 API——它没有。**
**正确做法就是读写 `config.txt`：APO 会监听这个文件，保存后自动重载（几百毫秒内生效）。**

**注意：**

```
· APO 只在「共享模式」音频流上生效
· 如果播放器用 WASAPI 独占 / ASIO，EQ 会被绕过
· 这一点要在 UI 上提示用户（"如果听不到变化，检查播放器是否独占"）
```

**验证切换是否生效的方法（可以做成 UI 里的"自检"按钮）**

```
读 config.txt 的 Include → 确认文件存在 → 确认文件内容非空
→ 提示 "已生效：<预设名>"
```

---

## 8. 预设内容参考（8 个，都在 presets/ 里）

| 文件 | 用途 | 关键参数 |
|---|---|---|
| `hd490pro-oratory-mix.txt` | 听歌（绒布耳罩，实测校准） | LSC 105 +5.5dB，1.3k -3dB，10k -4dB |
| `hd490pro-oratory-prod.txt` | 听歌（厚布耳罩） | LSC 110 +5.5dB，6k -4dB |
| `hd490pro.txt` | 手调：补低频+人声 | 1.2k +2.5dB，105 +3dB |
| `hd490pro-night.txt` | 夜间/低音量 | 80Hz +2.5dB，8.5k -1dB |
| `hd490pro-thick.txt` | 厚声模拟 | 90Hz +5dB，180 +3dB，2k -1.5dB |
| `hd490pro-game.txt` | 打瓦通用 | 200Hz -3dB，3.5k +1.5dB |
| `hd490pro-valorant.txt` | 打瓦专用（脚步） | 3.15k +4dB，200Hz -2dB，9k -2dB |
| `dt700.txt` | DT 700 Pro X 听歌 | oratory1990 实测预设 |

**每个文件都是标准 Equalizer APO 文本，可以直接复制给别的工具用。**

---

## 9. 建议的启动方式

```
EQ切换器.cmd（自提权）→ pythonw eq-switcher.py
```

**如果换成 PySide6 等，打包成 .exe 时注意：**

```
· 必须以管理员运行（写 Program Files）
· 需要 UAC manifest（requestedExecutionLevel = requireAdministrator）
· 或者保持"提权按钮"的模式，降低用户门槛
```

---

## 10. 一句话总结

> **它的核心只有一件事：把用户选的预设文件名写进 `C:\Program Files\EqualizerAPO\config\config.txt` 的 `Include:` 行。**
> **剩下的全部（UI、自动切换、曲线可视化、托盘、热键）都是围绕这件事的包装。**
