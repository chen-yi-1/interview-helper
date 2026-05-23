# Interview Helper - 面试助手

截图 + 区域选择 + OCR + DeepSeek AI，**全局热键**一键识别屏幕问题并显示答案。

## 安装

```bash
E:\miniconda3\envs\common\python.exe -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 配置

编辑 `config.json`，填入你的 DeepSeek API Key：

```json
{
  "deepseek_api_key": "sk-你的key"
}
```

## 使用

双击 `run.bat` 或在终端运行：

```bash
E:\miniconda3\envs\common\python.exe main.py
```

### 快捷键（全局，任何窗口下生效）

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+Shift+Z` | 框选截图区域 → OCR → AI 回答 |
| `Ctrl+Shift+X` | 隐藏/显示浮窗 |
| `Ctrl+Shift+H` | 退出程序 |
| `Alt` (按住) | 切换浮窗交互模式（拖拽/滚动） |
| 右键菜单 | 切换点击穿透 / 隐藏 / 退出 |

### 使用流程

1. 按 `Ctrl+Shift+Z` → 出现全屏半透明选区
2. **拖动鼠标**框选题目区域，松开自动识别
3. 按 `Esc` 取消截图
4. OCR 识别后自动发送到 DeepSeek AI
5. 浮窗显示结构化回答（思路 + 答案 + 代码 + 复杂度）
6. 浮窗默认**点击穿透**，不干扰操作
7. 按住 `Alt` 可拖拽浮窗位置

## 技术栈

- **GUI**: PySide6 (Qt6)
- **截图**: dxcam (Windows Desktop Duplication API)
- **OCR**: EasyOCR (中英文)
- **AI**: DeepSeek Chat API (结构化 JSON 输出)
- **全局热键**: WinAPI RegisterHotKey + QAbstractNativeEventFilter
- **浮窗**: 半透明无边框 Tool 窗口，WA_TransparentForMouseEvents 点击穿透

## 项目结构

| 文件 | 说明 |
|------|------|
| `main.py` | 入口 |
| `src/orchestrator.py` | 核心协调器，全局热键注册 |
| `src/overlay.py` | 悬浮窗，HTML 渲染回答 |
| `src/region_selector.py` | 全屏框选截图区域 |
| `src/screen_monitor.py` | dxcam 截图 + EasyOCR |
| `src/ai_client.py` | DeepSeek API 调用 |
| `src/audio_monitor.py` | 系统音频采集（可选） |

## 配置说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| deepseek_api_key | DeepSeek API Key | 必填 |
| model | 模型名 | deepseek-chat |
| temperature | 温度(0-1) | 0.3 |
| max_tokens | 最大输出长度 | 2048 |
| language | 语言 | zh |
| whisper_model | 语音模型 | base |
