#!/bin/bash
# UOS 远程服务端 - 联网一键安装脚本
# 在 UOS 上联网运行此脚本即可

set -e

echo "=========================================="
echo "UOS 远程服务端 - 联网安装"
echo "=========================================="
echo ""

# 检查是否联网
if ! ping -c 1 baidu.com &> /dev/null; then
    echo "错误: 无法连接网络，请检查网络连接"
    exit 1
fi

echo "[1/3] 更新软件源并安装系统依赖..."
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-tk python3-xlib \
    libjpeg-dev zlib1g-dev scrot imagemagick xdotool xclip

echo ""
echo "[2/3] 安装 Python 依赖..."
pip3 install pyinstaller pillow python-xlib

echo ""
echo "[3/3] 安装服务端..."
mkdir -p ~/uos_remote_server
cp uos_server.py test_uos_server.py ~/uos_remote_server/

echo ""
echo "=========================================="
echo "安装完成!"
echo "=========================================="
echo ""
echo "运行方式:"
echo "  1. 直接运行: cd ~/uos_remote_server && python3 uos_server.py"
echo "  2. 或构建可执行文件:"
echo "     cd ~/uos_remote_server"
echo "     pyinstaller --onefile --name uos_server uos_server.py"
echo "     ./uos_server"
echo ""
