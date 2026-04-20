#!/bin/bash
# 下载所有依赖包脚本
# 在能联网的 Debian/UOS 系统上运行，下载所有 .deb 包

set -e

echo "=========================================="
echo "UOS 远程服务端 - 依赖包下载工具"
echo "=========================================="
echo ""
echo "此脚本用于在联网机器上下载所有依赖的 .deb 包"
echo "下载完成后，将 offline_packages 目录复制到离线机器安装"
echo ""

# 创建输出目录
OUTPUT_DIR="offline_packages_$(date +%Y%m%d)"
mkdir -p "$OUTPUT_DIR"

echo "[1/3] 更新软件源..."
sudo apt-get update

echo ""
echo "[2/3] 下载依赖包..."

# 定义需要的包
PACKAGES="
python3
python3-pip
python3-dev
python3-tk
python3-xlib
python3-pil
python3-pil.imagetk
libjpeg-dev
zlib1g-dev
scrot
imagemagick
xdotool
xclip
x11-xserver-utils
libx11-6
libxext6
libxinerama1
libxrandr2
libxtst6
libxss1
"

# 下载所有依赖包
cd "$OUTPUT_DIR"

for pkg in $PACKAGES; do
    echo "  下载 $pkg ..."
    apt-get download $pkg 2>/dev/null || echo "  警告: $pkg 可能已安装或无法下载"
done

# 下载 python 依赖的 wheel 文件
echo ""
echo "[3/3] 下载 Python 依赖..."

mkdir -p pip_packages
cd pip_packages

pip3 download pyinstaller pillow python-xlib -d .

cd ..

echo ""
echo "=========================================="
echo "下载完成!"
echo "=========================================="
echo ""
echo "输出目录: $OUTPUT_DIR"
echo ""
echo "包含:"
echo "  - *.deb: 系统依赖包"
echo "  - pip_packages/: Python 依赖包"
echo ""
echo "使用方法:"
echo "1. 将整个 $OUTPUT_DIR 目录复制到离线 UOS 机器"
echo "2. 在离线机器上运行 install_offline.sh"
echo ""
