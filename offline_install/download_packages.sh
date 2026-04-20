#!/bin/bash
# 下载所有依赖包脚本
# 在能联网的 Debian/UOS/WSL 系统上运行，下载所有 .deb 包

set -e

echo "=========================================="
echo "UOS 远程服务端 - 依赖包下载工具"
echo "=========================================="
echo ""
echo "此脚本用于在联网机器上下载所有依赖的 .deb 包"
echo "支持: Debian/Ubuntu/UOS/WSL"
echo ""

# 检测是否在 WSL 中
if grep -q Microsoft /proc/version || grep -q WSL /proc/version; then
    echo "✓ 检测到 WSL 环境"
    IS_WSL=1
else
    IS_WSL=0
fi

# 检测架构
ARCH=$(dpkg --print-architecture)
echo "✓ 检测到架构: $ARCH"
echo ""

# 创建输出目录
OUTPUT_DIR="offline_packages_${ARCH}_$(date +%Y%m%d)"
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
libgiblib1
libimlib2
"

# 下载所有依赖包
cd "$OUTPUT_DIR"

# 先下载所有依赖的依赖
for pkg in $PACKAGES; do
    echo "  分析 $pkg 的依赖..."
    apt-get install --reinstall --print-uris $pkg 2>/dev/null | \
        grep "'http" | \
        cut -d"'" -f2 | \
        while read url; do
            filename=$(basename "$url")
            if [ ! -f "$filename" ]; then
                echo "    下载 $filename"
                wget -q "$url" || curl -sO "$url" || true
            fi
        done
done

# 再次确保主包已下载
for pkg in $PACKAGES; do
    echo "  下载 $pkg ..."
    apt-get download $pkg 2>/dev/null || echo "  警告: $pkg 可能已安装或无法下载"
done

echo ""
echo "[3/3] 下载 Python 依赖..."

mkdir -p pip_packages
cd pip_packages

pip3 download pyinstaller pillow python-xlib -d . --no-deps 2>/dev/null || \
    pip3 download pyinstaller pillow python-xlib -d .

cd ..

# 复制安装脚本
echo ""
echo "复制安装脚本..."
cd ..
cp install_offline.sh "$OUTPUT_DIR/"
cp README.txt "$OUTPUT_DIR/"

echo ""
echo "=========================================="
echo "下载完成!"
echo "=========================================="
echo ""
echo "输出目录: $OUTPUT_DIR"
echo ""
echo "包含:"
echo "  - *.deb: 系统依赖包 ($(ls "$OUTPUT_DIR"/*.deb 2>/dev/null | wc -l) 个)"
echo "  - pip_packages/: Python 依赖包"
echo "  - install_offline.sh: 安装脚本"
echo "  - README.txt: 使用说明"
echo ""
echo "使用方法:"
echo "1. 将整个 $OUTPUT_DIR 目录复制到离线 UOS 机器"
echo "2. 在离线机器上运行: ./install_offline.sh"
echo ""

# 打包
if command -v tar &> /dev/null; then
    echo "打包中..."
    tar -czf "${OUTPUT_DIR}.tar.gz" "$OUTPUT_DIR"
    echo "✓ 已打包: ${OUTPUT_DIR}.tar.gz"
fi
