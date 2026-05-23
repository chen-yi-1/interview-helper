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

# --- 2. AI Client: structured JSON ---
print("\n[2/5] AI structured JSON parsing...")
from src.ai_client import AIClient
ai = AIClient(config)

test_cases = [
    (
        '```json\n{"thought": "先分析", "answer": "答案是42", "code": "", "complexity": ""}\n```',
        "42"
    ),
    (
        '{"thought": "思路", "answer": "O(n)算法", "code": "print(1)", "complexity": "O(n)"}',
        "O(n)"
    ),
    (
        'plain text fallback',
        "plain text"
    ),
]
for raw, expected in test_cases:
    result = ai._parse_json(raw)
    check(f"parse json: {raw[:30]}", expected in str(result))

# --- 3. Hotkey manager ---
print("\n[3/5] Hotkey manager...")
from src.hotkey_manager import HotkeyManager
hm = HotkeyManager()
called = []
def test_cb():
    called.append(1)
hm.register('ctrl+shift+9', test_cb)
check("hotkey register", 'ctrl+shift+9' in hm._hotkeys)
hm.unregister_all()
check("hotkey unregister", len(hm._hotkeys) == 0)

# --- 4. Dependencies ---
print("\n[4/5] Dependencies...")
deps = [
    ("PySide6", "PySide6.QtWidgets"),
    ("dxcam", "dxcam"),
    ("easyocr", "easyocr"),
    ("faster_whisper", "faster_whisper"),
    ("sounddevice", "sounddevice"),
    ("httpx", "httpx"),
    ("keyboard", "keyboard"),
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
                    name_lower = dev['name'].lower()
                    if not any(kw in name_lower for kw in ['麦克风', 'microphone', 'mic ']):
                        loopback.append((dev_idx, dev['name'], int(dev['default_samplerate'])))
    if loopback:
        for idx, name, sr in loopback:
            print(f"  [{idx}] {name} ({sr} Hz)")
        check(f"found {len(loopback)} WASAPI loopback", True)
    else:
        print("  !! No WASAPI loopback found")
except Exception as e:
    print(f"  !! Audio check error: {e}")

# --- summary ---
print("\n" + "=" * 60)
print(f"Results: {ok} passed, {fail} failed")
print("=" * 60)
print()
print("Usage:")
print("  1. Set deepseek_api_key in config.json")
print("  2. Run: python main.py")
print("  3. Press Ctrl+Shift+Q to capture screen and ask AI")
print("  4. Hold Alt to interact with the overlay (scroll/drag)")
print("  5. Ctrl+Shift+H to toggle overlay visibility")
print("  6. Ctrl+Shift+X to quit")
