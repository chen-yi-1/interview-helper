# Interview Helper — 面试助手设计文档

日期: 2026-05-23
状态: 定稿

## 概述

Windows 桌面面试助手，全自动监听线上面试场景，通过系统音频捕获 + 屏幕 OCR 双通道识别面试官问题，调用 DeepSeek API 获取答案，以半透明浮窗显示在屏幕上。

## 架构

```
┌──────────────────────────────────────────────────────────────────┐
│                    Orchestrator（主调度器）                        │
│                   异步事件循环，协调各模块                        │
├──────────────┬───────────────┬──────────────┬───────────────────┤
│  屏幕捕获+OCR │  音频捕获+STT │  AI 集成      │  浮窗 UI           │
│              │               │  (DeepSeek)   │  (PyQt6)          │
├──────────────┼───────────────┼──────────────┼───────────────────┤
│  dxcam       │  PyAudio      │  httpx       │  无边框置顶窗口     │
│  每2-3秒截图  │  WASAPI       │  流式响应     │  半透明毛玻璃效果   │
│  PaddleOCR   │  faster-whisper│  上下文管理   │  可拖动/调大小     │
└──────────────┴───────────────┴──────────────┴───────────────────┘
```

## 模块设计

### 1. 屏幕捕获与 OCR（screen_monitor.py）

- **截图：** `dxcam` 库，Windows Desktop Duplication API，低 CPU 占用
- **频率：** 每 2 秒一次（可配置）
- **OCR：** `PaddleOCR`，中文模型，支持中英混合
- **增量检测：** 维护 OCR 文本历史，与上次结果对比，提取新出现的文字片段
- **过滤策略：** 包含疑问句式（?？吗呢么）或"请/你/如何/什么"等词的文本优先保留；明显无关的 UI 文字过滤掉

### 2. 音频捕获与语音识别（audio_monitor.py）

- **捕获：** `PyAudio` WASAPI loopback 模式，捕获扬声器输出
- **VAD：** `silero-vad` 检测语音活动区间，过滤静音段
- **STT：** `faster-whisper`，使用 `base` 模型，强制中文优先（`language=zh`）
- **句子检测：** 1.5 秒以上静音视为一句话结束

### 3. 问题检测与去重（question_detector.py）

- **双通道融合：** OCR 和音频各自独立判断"有新问题"
- **时间窗口合并：** 2 秒内来自不同通道的相似内容合并为一次提问
- **去重：** 模糊匹配（编辑距离），相同问题不重复提问
- **防抖：** 触发后 10 秒冷却期，防止反复触发
- **优先级：** OCR 文本优先（更准确），音频转录作为补充

### 4. AI 集成（ai_client.py）

- **API：** DeepSeek Chat API（`deepseek-chat`），`httpx` 异步流式请求
- **流式显示：** SSE 逐 token 更新 UI，模拟打字机效果
- **上下文：** 保留最近 3-5 轮问答用于连续追问
- **System Prompt：** 设定为面试助手角色，中文回答，要求简洁有条理
- **容错：** 超时重试 2 次、指数退避、网络断连提示

### 5. 浮窗 UI（overlay.py）

- **窗口：** PyQt6 `Qt.WindowStaysOnTopHint` 无边框置顶
- **样式：** 半透明（opacity 0.85）、深色主题、毛玻璃效果
- **交互：** 鼠标拖动、右下角缩放、右键菜单（隐藏/退出）
- **显示：** 顶部问题文本（可折叠） + 主体答案（流式更新） + 状态指示灯
- **快捷键：** `Ctrl+Shift+H` 隐藏/显示，`Ctrl+Shift+Q` 退出

### 6. 主调度器（orchestrator.py）

- **事件循环：** `asyncio` 驱动各模块协同
- **状态机：** 空闲 → 检测到问题 → AI 请求中 → 展示答案 → 空闲
- **生命周期：** 启动各模块 → 运行 → 资源清理

## 项目结构

```
interview-helper/
├── main.py                 # 入口
├── config.json             # 配置
├── requirements.txt        # 依赖
├── src/
│   ├── __init__.py
│   ├── orchestrator.py     # 主调度器
│   ├── screen_monitor.py   # 屏幕 + OCR
│   ├── audio_monitor.py    # 音频 + STT
│   ├── question_detector.py# 问题检测
│   ├── ai_client.py        # DeepSeek API
│   └── overlay.py          # PyQt6 浮窗
└── README.md
```

## 错误处理

- API 失败：重试 2 次 + 浮窗提示
- OCR 低置信度（< 0.6）：降级标记，优先用音频
- 音频设备变化：自动重连 WASAPI
- 内存控制：音频缓存 30 秒上限，OCR 历史 50 条上限
- 退出：`Ctrl+C` 或右键菜单均可干净释放资源

## 配置（config.json）

```json
{
  "deepseek_api_key": "",
  "model": "deepseek-chat",
  "temperature": 0.3,
  "max_tokens": 2048,
  "ocr_interval": 2.0,
  "vad_silence_threshold": 1.5,
  "cooldown_seconds": 10,
  "max_context_rounds": 5,
  "language": "zh"
}
```
