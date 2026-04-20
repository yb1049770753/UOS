#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UOS 服务端诊断脚本 - 用于排查启动问题
在 UOS 系统上运行此脚本查看详细错误信息
"""
import sys
import os
import traceback

print("=" * 60)
print("UOS 远程服务端诊断工具")
print("=" * 60)
print(f"Python 版本: {sys.version}")
print(f"Python 路径: {sys.executable}")
print(f"平台: {sys.platform}")
print(f"DISPLAY: {os.environ.get('DISPLAY', 'NOT SET')}")
print("-" * 60)

# 测试 tkinter
print("\n[1/5] 测试 tkinter...")
try:
    import tkinter as tk
    print(f"  tkinter 版本: {tk.Tcl().eval('info patchlevel')}")
    root = tk.Tk()
    print("  tkinter 初始化: OK")
    root.destroy()
except Exception as e:
    print(f"  tkinter 错误: {e}")
    traceback.print_exc()

# 测试 PIL
print("\n[2/5] 测试 PIL...")
try:
    from PIL import Image
    print(f"  PIL 版本: {Image.__version__}")
    img = Image.new('RGB', (100, 100), (255, 0, 0))
    print("  PIL 初始化: OK")
except Exception as e:
    print(f"  PIL 错误: {e}")
    traceback.print_exc()

# 测试截图工具
print("\n[3/5] 测试截图工具...")
screenshot_tools = ['scrot', 'import', 'gnome-screenshot', 'deepin-screenshot', 'xwd', 'xdg-screenshot']
for tool in screenshot_tools:
    try:
        import subprocess
        result = subprocess.run(['which', tool], capture_output=True, timeout=2)
        if result.returncode == 0:
            print(f"  {tool}: 可用 ({result.stdout.decode().strip()})")
        else:
            print(f"  {tool}: 未安装")
    except Exception as e:
        print(f"  {tool}: 检测失败 - {e}")

# 测试 xdotool
print("\n[4/5] 测试 xdotool...")
try:
    import subprocess
    result = subprocess.run(['which', 'xdotool'], capture_output=True, timeout=2)
    if result.returncode == 0:
        print(f"  xdotool: 可用 ({result.stdout.decode().strip()})")
    else:
        print(f"  xdotool: 未安装 (鼠标键盘控制将不可用)")
except Exception as e:
    print(f"  xdotool: 检测失败 - {e}")

# 测试 X11 连接
print("\n[5/5] 测试 X11 连接...")
try:
    import subprocess
    result = subprocess.run(['xset', 'q'], capture_output=True, timeout=2)
    if result.returncode == 0:
        print("  X11 连接: OK")
    else:
        print(f"  X11 连接: 失败 (退出码 {result.returncode})")
        print(f"  错误输出: {result.stderr.decode()[:200]}")
except Exception as e:
    print(f"  X11 连接: 失败 - {e}")

print("\n" + "=" * 60)
print("诊断完成")
print("=" * 60)

# 检查 uos_server.py 是否存在 UOSServerGUI 类
print("\n检查 uos_server.py...")
print("-" * 60)
try:
    with open('uos_server.py', 'r', encoding='utf-8') as f:
        content = f.read()
        if 'class UOSServerGUI' in content:
            print("✓ uos_server.py 包含 UOSServerGUI 类")
        else:
            print("✗ uos_server.py 缺少 UOSServerGUI 类 (文件可能是旧版本)")
except Exception as e:
    print(f"读取 uos_server.py 失败: {e}")

print("\n" + "=" * 60)
print("诊断完成")
print("=" * 60)
print("\n建议:")
print("1. 如果截图工具都未安装，请运行:")
print("   sudo apt-get install scrot imagemagick")
print("2. 如果 uos_server.py 是旧版本，请更新到最新代码")
input("\n按 Enter 键退出...")
