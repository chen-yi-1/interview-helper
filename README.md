# Interview Helper - 面试助手

自动监听线上面试，捕获屏幕文字 + 系统音频，识别面试官问题，通过 DeepSeek AI 实时显示答案。

## 安装

```bash
E:\miniconda3\envs\common\python.exe -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 配置

编辑 `config.json`，填入你的 DeepSeek API Key：

```json
{
  "deepseek_api_key": "sk-你的key",
  "model": "deepseek-chat",
  "temperature": 0.3
}
```

## 使用

双击 `run.bat` 或在终端运行：

```bash
E:\miniconda3\envs\common\python.exe main.py
```

启动后浮窗会显示在屏幕右下角：

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+Shift+H` | 隐藏/显示浮窗 |
| `Ctrl+Shift+Q` | 退出程序 |
| 鼠标拖拽 | 移动浮窗位置 |
| 右键菜单 | 隐藏/退出 |

## 工作流程

1. 屏幕每 2 秒 OCR 识别 + 系统音频持续监听
2. 检测到问题文本（含问句特征）后自动去重、合并
3. 发送到 DeepSeek API，流式获取答案
4. 答案逐字显示在浮窗上

## 配置说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| deepseek_api_key | DeepSeek API Key | 必填 |
| model | 模型名 | deepseek-chat |
| temperature | 温度(0-1) | 0.3 |
| max_tokens | 最大输出长度 | 2048 |
| ocr_interval | OCR 截屏间隔(秒) | 2.0 |
| cooldown_seconds | 问题触发冷却(秒) | 10 |
| max_context_rounds | 上下文保留轮数 | 5 |
| language | 语言 | zh |
| whisper_model | 语音模型 | base |
