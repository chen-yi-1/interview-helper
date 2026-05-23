import json
import re
from PySide6.QtCore import QThread, Signal
import httpx


STRUCTURED_PROMPT = """你是一个专业面试助手。请分析下面的问题并用 JSON 格式回答。

{{
  "thought": "解题思路分析，用中文简要说明如何得出答案",
  "answer": "问题的直接答案，用中文清晰表述",
  "code": "如果涉及代码，在此给出；否则留空",
  "complexity": "如果涉及算法，给出时间和空间复杂度；否则留空"
}}

只输出 JSON，不要包含其他文字。问题如下："""


class AIClient(QThread):
    response_ready = Signal(dict)
    response_token = Signal(str)

    def __init__(self, config):
        super().__init__()
        self.api_key = config['deepseek_api_key']
        self.model = config.get('model', 'deepseek-chat')
        self.base_url = config.get('base_url', 'https://api.deepseek.com')
        self.temperature = config.get('temperature', 0.3)
        self.max_tokens = config.get('max_tokens', 2048)
        self.max_context = config.get('max_context_rounds', 5)
        self.system_prompt = config.get('system_prompt')

        self.messages = []
        self.current_question = ""
        self._abort = False

    def ask(self, question: str):
        self.current_question = question
        self.messages.append({"role": "system", "content": self.system_prompt or "你是一个专业面试助手。"})
        self.messages.append({"role": "user", "content": STRUCTURED_PROMPT + question})
        self._abort = False
        self.start()

    def run(self):
        full_text = ""

        try:
            with httpx.Client(timeout=60) as client:
                response = client.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": STRUCTURED_PROMPT + self.current_question}],
                        "temperature": self.temperature,
                        "max_tokens": self.max_tokens,
                        "stream": True,
                    },
                )

                for line in response.iter_lines():
                    if self._abort:
                        break
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        data = json.loads(data_str)
                        choices = data.get('choices', [])
                        if choices:
                            delta = choices[0].get('delta', {})
                            content = delta.get('content', '')
                            if content:
                                full_text += content
                                self.response_token.emit(content)

        except Exception as e:
            full_text = json.dumps({"answer": f"[错误: {e}]", "thought": "", "code": "", "complexity": ""})

        parsed = self._parse_json(full_text)
        self.response_ready.emit(parsed)

        # Trim context (keep last N exchanges)
        max_msgs = self.max_context * 2 + 1
        if len(self.messages) > max_msgs:
            self.messages = [self.messages[0]] + self.messages[-(max_msgs - 1):]

    def _parse_json(self, text: str) -> dict:
        """Extract JSON from LLM response (handles markdown wrapping)."""
        # Try direct parse
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r'^```(?:json)?\s*', '', text)
            text = re.sub(r'\s*```$', '', text)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # Fallback: find {...} block
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
        # Last resort: wrap raw text as answer
        return {"thought": "", "answer": text, "code": "", "complexity": ""}

    def abort(self):
        self._abort = True
