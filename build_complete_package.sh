#!/bin/bash
# 完整的 UOS 远程服务端离线包构建脚本
# 包含所有依赖的二进制文件

set -e

echo "=========================================="
echo "UOS 远程服务端完整离线包构建"
echo "=========================================="
echo ""

ARCH=$(uname -m)
if [ "$ARCH" = "x86_64" ]; then
    PKG_NAME="UOS远程服务端_v1.1_AMD64"
elif [ "$ARCH" = "aarch64" ]; then
    PKG_NAME="UOS远程服务端_v1.1_ARM64"
else
    PKG_NAME="UOS远程服务端_v1.1_$ARCH"
fi

BUILD_DIR="build_package_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BUILD_DIR/bin"
mkdir -p "$BUILD_DIR/lib"

echo "[1/6] 收集依赖的二进制文件..."

# 复制截图工具
for tool in scrot import xwd convert; do
    if command -v $tool &> /dev/null; then
        cp "$(which $tool)" "$BUILD_DIR/bin/" 2>/dev/null || echo "跳过 $tool"
        echo "  ✓ $tool"
    fi
done

# 复制 xdotool
if command -v xdotool &> /dev/null; then
    cp "$(which xdotool)" "$BUILD_DIR/bin/"
    echo "  ✓ xdotool"
fi

# 复制其他依赖
for dep in xclip xsel; do
    if command -v $dep &> /dev/null; then
        cp "$(which $dep)" "$BUILD_DIR/bin/" 2>/dev/null || true
    fi
done

echo ""
echo "[2/6] 收集库文件..."

# 收集依赖的库
for binary in "$BUILD_DIR/bin/"*; do
    if [ -f "$binary" ]; then
        ldd "$binary" 2>/dev/null | grep "=> /" | awk '{print $3}' | while read lib; do
            if [ -f "$lib" ] && [ ! -f "$BUILD_DIR/lib/$(basename $lib)" ]; then
                cp "$lib" "$BUILD_DIR/lib/" 2>/dev/null || true
            fi
        done
    fi
done
echo "  ✓ 库文件收集完成"

echo ""
echo "[3/6] 构建主程序..."

# 清理并构建
rm -rf build dist __pycache__

pyinstaller --onefile \
    --name "uos_server" \
    --hidden-import PIL \
    --hidden-import tkinter \
    --hidden-import Xlib \
    --hidden-import Xlib.display \
    --hidden-import Xlib.X \
    uos_server.py

cp "dist/uos_server" "$BUILD_DIR/"
echo "  ✓ 主程序构建完成"

echo ""
echo "[4/6] 复制源码和工具..."

cp uos_server.py "$BUILD_DIR/"
cp test_uos_server.py "$BUILD_DIR/"

echo ""
echo "[5/6] 创建启动器脚本..."

cat > "$BUILD_DIR/run.sh" << 'EOF'
#!/bin/bash
# UOS 远程服务端启动脚本

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
export PATH="$SCRIPT_DIR/bin:$PATH"
export LD_LIBRARY_PATH="$SCRIPT_DIR/lib:$LD_LIBRARY_PATH"

# 检查 DISPLAY
if [ -z "$DISPLAY" ]; then
    export DISPLAY=:0
fi

# 运行服务端
exec "$SCRIPT_DIR/uos_server" "$@"
EOF

chmod +x "$BUILD_DIR/run.sh"
chmod +x "$BUILD_DIR/uos_server"
chmod +x "$BUILD_DIR/bin/"* 2>/dev/null || true

echo ""
echo "[6/6] 创建 README..."

cat > "$BUILD_DIR/README.txt" << EOF
UOS 远程控制服务端 v1.1 - 完整离线包
=====================================

架构: $ARCH
打包日期: $(date +%Y-%m-%d)

【文件说明】
- uos_server: 主程序
- run.sh: 启动脚本（推荐）
- bin/: 依赖的二进制工具
  * scrot - 截图工具
  * import - ImageMagick 截图
  * xwd - X11 截图
  * convert - 图像转换
  * xdotool - 鼠标键盘控制
- lib/: 依赖的库文件
- uos_server.py: Python 源码
- test_uos_server.py: 诊断工具

【使用方法】

方法1 - 使用启动脚本（推荐）:
  ./run.sh

方法2 - 直接运行:
  ./uos_server

【系统要求】
- Linux 系统 (UOS/Deepin/Debian/Ubuntu)
- X11 显示环境
- $ARCH 架构

【故障排查】
1. 如果提示缺少库文件:
   export LD_LIBRARY_PATH="$(pwd)/lib:\$LD_LIBRARY_PATH"
   ./uos_server

2. 查看详细日志:
   cat ~/uos_server_debug.log

3. 运行诊断工具:
   python3 test_uos_server.py

【注意事项】
- 首次运行可能需要赋予执行权限: chmod +x run.sh uos_server
- 确保系统已启用 X11 显示 (:0)
EOF

echo ""
echo "打包中..."
tar -czf "${PKG_NAME}.tar.gz" "$BUILD_DIR"

echo ""
echo "=========================================="
echo "构建完成!"
echo "=========================================="
echo ""
echo "输出文件: ${PKG_NAME}.tar.gz"
echo ""
echo "使用方法:"
echo "1. 将 ${PKG_NAME}.tar.gz 复制到 UOS 系统"
echo "2. 解压: tar -xzf ${PKG_NAME}.tar.gz"
echo "3. 进入目录: cd $BUILD_DIR"
echo "4. 运行: ./run.sh"
echo ""
