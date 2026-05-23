#!/usr/bin/env python3
"""Interview Helper - Test Suite"""
import sys
import os
import json
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
print("=" * 60)
print("Interview Helper - Test Suite")
print("=" * 60)

# --- helpers ---
ok = 0
fail = 0

def check(name, condition, detail=""):
    global ok, fail
    if condition:
        ok += 1
        print(f"  PASS [{name}]")
    else:
        fail += 1
        print(f"  FAIL [{name}] {detail}")

# --- 1. Config ---
print("\n[1/5] Config check...")
config_path = os.path.join(os.path.dirname(__file__), 'config.json')
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)
for k in ['deepseek_api_key', 'model', 'base_url', 'temperature', 'max_tokens']:
    check(f"config.{k}", k in config)
if config.get('deepseek_api_key'):
    print(f"  API Key: {config['deepseek_api_key'][:8]}...")
else:
    print("  !! API Key not set - AI test will be skipped")

# --- 2. Question Detector ---
print("\n[2/5] Question detector...")
from src.question_detector import QuestionDetector
qd = QuestionDetector(config)

pos_cases = [
    "请解释什么是多态",
    "你能说说TCP和UDP的区别吗",
    "什么是死锁？",
    "描述一下你做过的最有挑战的项目",
    "HashMap和ConcurrentHashMap有什么区别",
    "请介绍一下项目架构",
    "什么是指针",
    "如何优化SQL查询性能",
    "有哪些设计模式",
    "Java和Go有什么区另",
]
for q in pos_cases:
    check(f"positive: {q[:20]}", qd._looks_like_question(q))

neg_cases = [
    "这是一段普通代码",
    "int x = 1;",
    "System.out.println",
    "const data = fetch(url)",
]
for nq in neg_cases:
    check(f"negative: {nq[:20]}", not qd._looks_like_question(nq))

h1 = qd._hash("请解释什么是多态")
h2 = qd._hash("请解释什么是多态")
check("dedup hash", h1 == h2)
check("initial can trigger", qd._can_trigger())

# --- 3. DeepSeek API ---
print("\n[3/5] DeepSeek API...")
from src.ai_client import AIClient

api_key = config.get('deepseek_api_key', '')
if api_key:
    ai = AIClient(config)
    check("AIClient created", ai is not None)
    check("system prompt set", len(ai.messages) == 1 and ai.messages[0]['role'] == 'system')
    print("  (streaming API call requires QApp event loop - run main.py to verify)")
else:
    print("  SKIP (no API key configured)")
    print("  Set deepseek_api_key in config.json to enable AI")

# --- 4. Dependencies ---
print("\n[4/5] Dependencies...")
deps = [
    ("PySide6", "PySide6.QtWidgets"),
    ("dxcam", "dxcam"),
    ("easyocr", "easyocr"),
    ("faster_whisper", "faster_whisper"),
    ("sounddevice", "sounddevice"),
    ("silero_vad", "silero_vad"),
    ("scipy.signal", "scipy.signal"),
    ("httpx", "httpx"),
]
for name, mod in deps:
    try:
        exec(f"import {mod.split('.')[0]}")
        check(f"{name}", True)
    except Exception as e:
        check(f"{name}", False, str(e))

# --- 5. Audio devices ---
print("\n[5/5] Audio devices...")
try:
    import sounddevice as sd
    hostapis = sd.query_hostapis()
    loopback = []
    for ha in hostapis:
        if 'wasapi' in ha['name'].lower():
            for dev_idx in ha['devices']:
                dev = sd.query_devices(dev_idx)
                if dev['max_input_channels'] > 0:
                    loopback.append((dev_idx, dev['name'], int(dev['default_samplerate'])))
    if loopback:
        for idx, name, sr in loopback:
            print(f"  [{idx}] {name} ({sr} Hz)")
        check(f"found {len(loopback)} WASAPI loopback devices", True)
    else:
        print("  !! No WASAPI loopback device found")
        print("  Audio will fall back but screen+AI still works")
except Exception as e:
    print(f"  !! Audio check error: {e}")

# --- summary ---
print("\n" + "=" * 60)
print(f"Results: {ok} passed, {fail} failed")
print("=" * 60)
print()
print("Manual test steps:")
print("  1. Set deepseek_api_key in config.json")
print("  2. Run: python main.py")
print("  3. Floating overlay should show [Listening...]")
print("  4. Play a Chinese video - watch for recognized text")
print("  5. Ctrl+Shift+H to toggle overlay")
print("  6. Ctrl+Shift+Q to quit")
