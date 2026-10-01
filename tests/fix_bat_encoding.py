"""把 start.bat 规范化为 CP936(ANSI) + CRLF，并校验「逻辑行全为 ASCII」。

为什么需要它
-----------
cmd.exe 按系统 ANSI 代码页**逐字节**解析 .bat 文件，而且解析发生在
`chcp 65001` 生效**之前**。如果文件存成 UTF-8：

  1. 中文注释被按 CP936 解码成乱码；
  2. 乱码里的字节可能等于命令分隔符，把一条语句拆成多条；
  3. `set` / `if` / `goto` 一旦被拆碎，双击后就满屏
     「'xxx' 不是内部或外部命令，也不是可运行的程序或批处理文件」。

修复思路（两条一起用才稳）：
  * 命令逻辑只用 ASCII，中文只出现在 echo 里；
  * 文件以 CP936 落盘。

用法：python tests/fix_bat_encoding.py
退出码：0 表示已修复且校验通过，1 表示校验未通过。
"""
from __future__ import annotations

import sys
from pathlib import Path

BAT = Path(__file__).resolve().parent.parent / "start.bat"
CP936 = "cp936"

# 中文回读检查用的锚点（启动横幅已移交 Python 打印，因此这里检查 ASCII 提示语）
ANCHORS = ["Python not found"]
REQUIRED_COMMANDS = [
    "where py",
    'if not errorlevel 1 set "PYTHON=py"',
    'set "EXITCODE=%ERRORLEVEL%"',
    "backend\\app.py",
]


def read_any_encoding(path: Path) -> tuple[str, str]:
    """优先按 CP936 读（正常状态），失败再按 UTF-8 读（被编辑器存成 UTF-8 的情况）。"""
    raw = path.read_bytes()
    if raw[:3] == b"\xef\xbb\xbf":
        return raw.decode("utf-8-sig"), "utf-8-sig"
    try:
        text = raw.decode(CP936)
        # 如果 CP936 解出来的内容里出现典型 UTF-8 中文被误解的乱码，说明原文件是 UTF-8
        if "锛" in text or "浣" in text or "鐨" in text:
            return raw.decode("utf-8"), "utf-8(疑似)"
        return text, CP936
    except UnicodeDecodeError:
        return raw.decode("utf-8"), "utf-8"


def main() -> int:
    if not BAT.exists():
        print(f"FAIL 找不到 {BAT}")
        return 1

    text, detected = read_any_encoding(BAT)
    print(f"读取 {BAT.name}：按 {detected} 解码成功")

    # 统一 CRLF：.bat 的惯例，也让 cmd 的逐行解析更稳定
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r\n")

    try:
        payload = normalized.encode(CP936)
    except UnicodeEncodeError as exc:
        print(f"FAIL 存在 CP936 无法表示的字符，请改用 ASCII 或全角字符替代：{exc}")
        return 1

    changed = payload != BAT.read_bytes()
    BAT.write_bytes(payload)
    print(f"{'已重新写入' if changed else '无需修改'}：{len(payload)} 字节，CP936，无 BOM")

    # ---------------- 校验 ----------------
    data = BAT.read_bytes()
    ok = True

    if data[:3] == b"\xef\xbb\xbf":
        ok = False
        print("FAIL 文件带有 UTF-8 BOM，cmd 会把首行当作乱码命令")

    try:
        lines = data.decode(CP936).splitlines()
    except UnicodeDecodeError as exc:
        print(f"FAIL 无法按 CP936 回读：{exc}")
        return 1

    non_ascii_logic = []
    for index, line in enumerate(lines, 1):
        stripped = line.strip()
        lowered = stripped.lower()
        is_logic = bool(stripped) and not lowered.startswith(("rem", "echo", "@echo", "::"))
        if is_logic and any(ord(ch) > 127 for ch in line):
            non_ascii_logic.append((index, stripped))

    if non_ascii_logic:
        ok = False
        print("FAIL 以下逻辑行含非 ASCII 字符，必须改成纯 ASCII：")
        for index, line in non_ascii_logic:
            print(f"  第 {index} 行: {line}")
    else:
        print("逻辑行检查：全部为 ASCII，解析安全")

    if data.count(b"\r\n") != len(lines) - 1 and not data.endswith(b"\r\n"):
        print("提示：换行未完全统一为 CRLF")

    for anchor in ANCHORS:
        found = any(anchor in line for line in lines)
        print(f"中文回读 {anchor!r}：{'OK' if found else '未找到'}")
        if not found:
            ok = False

    for command in REQUIRED_COMMANDS:
        found = any(command in line for line in lines)
        print(f"关键命令 {command!r}：{'存在' if found else '缺失'}")
        if not found:
            ok = False

    # chcp 65001 会让 CP936 文件里的中文变成双重编码乱码，必须不能出现为实际命令
    chcp_cmd = [
        (i, line.strip()) for i, line in enumerate(lines, 1)
        if line.strip().lower().startswith("chcp")
    ]
    if chcp_cmd:
        ok = False
        print("FAIL 检测到 chcp 命令，它会让 CP936 内容变成双重编码乱码：")
        for index, line in chcp_cmd:
            print(f"  第 {index} 行: {line}")
    else:
        print("chcp 检查：未出现 chcp 命令（正确）")

    print("\n结果：" + ("通过，双击 start.bat 可正常解析" if ok else "未通过，请按上面提示修正"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
