#!/bin/bash
# 离线安装脚本
# 在离线 UOS 机器上运行此脚本安装所有依赖

set -e

echo "=========================================="
echo "UOS 远程服务端 - 离线安装程序"
echo "=========================================="
echo ""

# 找到包含 .deb 包的目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "[1/4] 安装系统依赖包..."
cd "$SCRIPT_DIR"

# 安装所有 .deb 包
if ls *.deb 1> /dev/null 2>&1; then
    echo "  找到 $(ls *.deb | wc -l) 个 .deb 包"
    sudo dpkg -i *.deb || {
        echo "  尝试修复依赖..."
        sudo apt-get install -f -y
    }
else
    echo "  警告: 未找到 .deb 包"
fi

echo ""
echo "[2/4] 安装 Python 依赖..."

if [ -d "pip_packages" ]; then
    cd pip_packages
    pip3 install --no-index --find-links . pyinstaller pillow python-xlib
    cd ..
else
    echo "  警告: 未找到 pip_packages 目录"
fi

echo ""
echo "[3/4] 检查安装结果..."

# 检查关键依赖
echo "  检查 Python3..."
python3 --version || echo "  ✗ Python3 未安装"

echo "  检查 tkinter..."
python3 -c "import tkinter; print('  ✓ tkinter OK')" || echo "  ✗ tkinter 未安装"

echo "  检查 PIL..."
python3 -c "from PIL import Image; print('  ✓ PIL OK')" || echo "  ✗ PIL 未安装"

echo "  检查截图工具..."
for tool in scrot import xwd convert; do
    if command -v $tool &> /dev/null; then
        echo "  ✓ $tool"
    else
        echo "  ✗ $tool 未安装"
    fi
done

echo "  检查 xdotool..."
if command -v xdotool &> /dev/null; then
    echo "  ✓ xdotool"
else
    echo "  ✗ xdotool 未安装"
fi

echo ""
echo "[4/4] 安装服务端..."

# 复制服务端脚本
if [ -f "../uos_server.py" ]; then
    mkdir -p ~/uos_remote_server
    cp ../uos_server.py ~/uos_remote_server/
    cp ../test_uos_server.py ~/uos_remote_server/
    echo "  ✓ 服务端脚本已复制到 ~/uos_remote_server/"
else
    echo "  警告: 未找到 uos_server.py"
fi

echo ""
echo "=========================================="
echo "安装完成!"
echo "=========================================="
echo ""
echo "使用方法:"
echo "  cd ~/uos_remote_server"
echo "  python3 uos_server.py"
echo ""
echo "或者构建独立可执行文件:"
echo "  cd ~/uos_remote_server"
echo "  pyinstaller --onefile --name uos_server uos_server.py"
echo "  ./uos_server"
echo ""
