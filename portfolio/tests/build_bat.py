"""把 start.bat.utf8 转成 CP936 的 start.bat（Python 工具，避免手写编码出错）。

用法：python tests/build_bat.py
"""
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent.parent
SRC = BASE / "start.bat.utf8"
DST = BASE / "start.bat"

text = SRC.read_text(encoding="utf-8")
text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r\n")

non_ascii = [(i, ln) for i, ln in enumerate(text.splitlines(), 1) if any(ord(c) > 127 for c in ln)]
if non_ascii:
    print("警告：以下行含非 ASCII 字符（.bat 应保持纯 ASCII）：")
    for i, ln in non_ascii:
        print(f"  {i}: {ln}")

try:
    payload = text.encode("cp936")
except UnicodeEncodeError as exc:
    print(f"FAIL 无法用 CP936 编码：{exc}")
    sys.exit(1)

DST.write_bytes(payload)
print(f"已生成 {DST.name}：{len(payload)} 字节，CP936，无 BOM")
print("含 chcp 65001:", "chcp 65001" in text)
