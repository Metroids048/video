# 跨平台路径与差异处理

cut.skill 支持 Windows 与 macOS。Linux 因剪映/Premiere 无官方版本不支持。

## 1. 剪映 draft 文件路径

### Windows（剪映专业版）

```
%LOCALAPPDATA%\JianyingPro\User Data\Projects\com.lveditor.draft\
```

展开后类似：
```
C:\Users\<用户名>\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft\
```

### Windows（CapCut 国际版）

```
%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft\
```

### macOS（剪映专业版）

```
~/Movies/JianyingPro/User Data/Projects/com.lveditor.draft/
```

部分版本可能在：
```
~/Library/Application Support/JianyingPro/User Data/Projects/com.lveditor.draft/
```

### macOS（CapCut 国际版）

```
~/Movies/CapCut/User Data/Projects/com.lveditor.draft/
```

## 2. 自动检测

`cut.platform.detect()` 会自动找路径。检测逻辑：

1. 依次检查上述所有候选路径
2. 第一个存在的路径作为 `drafts_dir`
3. 找到 `drafts_dir` 后，扫描子目录，读最新修改的 `draft_content.json` 推断版本号

## 3. 手动指定

如果自动检测失败（如自定义安装路径），用环境变量：

```bash
# Linux/macOS
export CUT_DRAFTS_DIR="/custom/path/to/drafts"

# Windows PowerShell
$env:CUT_DRAFTS_DIR = "D:\MyJianying\Drafts"
```

或在 Python 中：

```python
import os
os.environ["CUT_DRAFTS_DIR"] = "/custom/path"
from cut.jianying.draft import Draft
draft = Draft.open(project_name="my_vlog")
```

## 4. Premiere 安装路径

### Windows

```
C:\Program Files\Adobe\Adobe Premiere Pro 2024\
```

`cut.platform._detect_premiere()` 会扫描 `Program Files\Adobe` 下所有
`Adobe Premiere Pro YYYY` 目录。

### macOS

```
/Applications/Adobe Premiere Pro 2024/
```

## 5. Premiere 是否运行

检测方法：
- **Windows**：`tasklist /FI "IMAGENAME eq Adobe Premiere Pro.exe"`
- **macOS**：`pgrep -i premiere`

不依赖 psutil，避免额外依赖。

## 6. Python 依赖差异

| 包 | Windows | macOS | 用途 |
|---|---|---|---|
| `pymiere` | ✅ | ✅ | Premiere 操控 |
| `pyautogui` | ✅ | ✅ | UI 自动化（剪映导出） |
| `pygetwindow` | ✅ | ❌（用 pyobjc） | 窗口控制 |
| `pywinauto` | ✅ | ❌ | Windows UI 自动化 |
| `AppKit` | ❌ | ✅（系统自带） | macOS 窗口控制 |
| `flask` | ✅ | ✅ | HTTP API |
| `mcp` | ✅ | ✅ | MCP Server |
| `ffmpeg` | 系统命令 | 系统命令 | 媒体探测与导出 |

## 7. 文件路径分隔符

Python 的 `pathlib.Path` 自动处理分隔符，**永远用 Path 不要用字符串拼接**：

```python
# ✅ 正确
from pathlib import Path
p = Path(home) / "Movies" / "JianyingPro" / "draft_content.json"

# ❌ 错误（Windows 会失败）
p = home + "/Movies/JianyingPro/draft_content.json"
```

剪映 draft 中的 `path` 字段是绝对路径，使用所在平台的分隔符。修改时保持一致。

## 8. 剪映版本差异

### 4.x vs 5.x

- **4.x**：`materials.videos` 的字段较少，没有 `intensifies_path`、`mask_info` 等
- **5.x**：增加了 `material_animations`、`fursuer_effect`、`responsive_layout` 等
- 字段名 `text` 在 4.x 是 `content`，5.x 两者都有

`Draft.open()` 会读 `draft_version` 字段判断版本，5.x 之前的版本会发出警告但继续。

### CapCut vs 剪映

draft schema 完全一致，只是：
- 默认安装路径不同
- 内置特效/转场 ID 因地区可能有差异
- CapCut 没有"剪映云"相关字段

## 9. 字体路径

剪映 text material 的 `font_path` 字段：

- **Windows**：`C:\Windows\Fonts\msyh.ttc`
- **macOS**：`/System/Library/Fonts/PingFang.ttc` 或 `/Library/Fonts/`

留空时使用剪映默认字体。

## 10. 媒体文件路径

draft 中 `material.path` 是导入时的绝对路径。如果项目在另一台机器打开，
路径会失效。解决方案：

1. 用相对路径（剪映原生不支持，但可以通过脚本转换）
2. 用"代理文件"模式
3. 移植项目时同步移动素材并修改 path

cut.skill 当前不处理跨机器移植，假设在本机操作。

## 11. 环境变量总览

| 变量 | 默认 | 说明 |
|---|---|---|
| `CUT_DRAFTS_DIR` | 自动检测 | 剪映 draft 根目录 |
| `CUT_API_PORT` | 8765 | HTTP API 端口 |
| `CUT_API_HOST` | 127.0.0.1 | HTTP API 监听地址 |

## 12. 故障排查

### "未找到剪映 draft 目录"

1. 确认剪映专业版（不是手机版/网页版）已安装
2. 在剪映中至少创建一个项目（首次创建会生成 draft 目录）
3. 检查路径是否在标准位置
4. 设置 `CUT_DRAFTS_DIR` 环境变量

### "未找到 Premiere"

1. 确认是 Premiere Pro（不是 Premiere Elements / Premiere Rush）
2. 检查 `Program Files\Adobe\` (Win) 或 `/Applications/` (Mac)
3. 自定义安装路径无法自动检测，需手动修改 `_detect_premiere()`

### "pymiere 连接失败"

见 `references/premiere-operations.md` 第 15 节。
