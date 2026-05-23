# Interview Helper - 面试助手

截图 + OCR + DeepSeek AI，按 `Ctrl+Shift+Q` 一键识别屏幕问题并显示答案。

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

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+Shift+Q` | 截图 + OCR + AI 问答 |
| `Alt` (按住) | 切换浮窗交互模式（拖拽/滚动） |
| `Ctrl+Shift+H` | 隐藏/显示浮窗 |
| `Ctrl+Shift+X` | 退出程序 |
| 右键菜单 | 切换点击穿透 / 隐藏 / 退出 |

## 工作流程

1. 按 `Ctrl+Shift+Q` → 截取当前屏幕
2. EasyOCR 识别屏幕文字
3. DeepSeek AI 结构化输出（思路 + 答案 + 代码 + 复杂度）
4. 浮窗显示结果，默认点击穿透不干扰操作

## 配置说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| deepseek_api_key | DeepSeek API Key | 必填 |
| model | 模型名 | deepseek-chat |
| temperature | 温度(0-1) | 0.3 |
| max_tokens | 最大输出长度 | 2048 |
| language | 语言 | zh |
| whisper_model | 语音模型 | base |
