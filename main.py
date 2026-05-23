#!/usr/bin/env python3
"""Interview Helper - 面试助手"""
import sys
import json
import os


def load_config():
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    config = load_config()

    if not config.get('deepseek_api_key'):
        print("错误: 请在 config.json 中配置 deepseek_api_key")
        sys.exit(1)

    from src.orchestrator import Orchestrator
    app = Orchestrator(config)
    app.run()


if __name__ == '__main__':
    main()
