import json
from PySide6.QtCore import QThread, Signal
import httpx


class AIClient(QThread):
    response_start = Signal()
    response_token = Signal(str)

    def __init__(self, config):
        super().__init__()
        self.api_key = config['deepseek_api_key']
        self.model = config.get('model', 'deepseek-chat')
        self.base_url = config.get('base_url', 'https://api.deepseek.com')
        self.temperature = config.get('temperature', 0.3)
        self.max_tokens = config.get('max_tokens', 2048)
        self.system_prompt = config.get(
            'system_prompt',
            '你是一个专业面试助手。请用中文清晰、有条理地回答问题。'
            '如果是编程题，先给出解题思路，再给出代码。'
            '如果是概念题，给出定义、要点和例子。回答要简洁但全面。'
        )
        self.max_context = config.get('max_context_rounds', 5)

        self.messages = [{"role": "system", "content": self.system_prompt}]
        self._abort = False

    def ask(self, question: str):
        self._abort = False
        self.messages.append({"role": "user", "content": question})
        if not self.isRunning():
            self.start()

    def run(self):
        self.response_start.emit()
        full_response = ""

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
                        "messages": self.messages,
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
                                full_response += content
                                self.response_token.emit(content)

        except Exception as e:
            self.response_token.emit(f"\n\n[错误: {e}]")

        self.messages.append({"role": "assistant", "content": full_response})

        # Trim context window
        max_msgs = self.max_context * 2 + 1
        if len(self.messages) > max_msgs:
            self.messages = [self.messages[0]] + self.messages[-(max_msgs - 1):]

    def abort(self):
        self._abort = True
