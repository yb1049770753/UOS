#!/bin/bash
# 打包已安装的环境
# 在当前UOS机器上运行，收集所有已安装的依赖并打包

set -e

echo "=========================================="
echo "UOS 远程服务端 - 环境打包工具"
echo "=========================================="
echo ""

# 打包输出目录
OUTPUT_DIR="UOS_Server_Install_Package_$(date +%Y%m%d)"
mkdir -p "$OUTPUT_DIR"

echo "[1/4] 收集已安装的 .deb 包..."

# 获取已安装的关键包列表
PACKAGES="python3 python3-pip python3-tk python3-xlib scrot imagemagick xdotool xclip libjpeg-dev zlib1g-dev"

# 下载已安装包的 .deb 文件
mkdir -p "$OUTPUT_DIR/debs"
cd "$OUTPUT_DIR/debs"

for pkg in $PACKAGES; do
    if dpkg -l | grep -q "^ii  $pkg "; then
        echo "  收集 $pkg ..."
        # 下载该包及其依赖
        apt-get download $pkg 2>/dev/null || true
        # 获取依赖并下载
        deps=$(apt-cache depends --recurse --no-recommends --no-suggests --no-conflicts --no-breaks --no-replaces --no-enhances $pkg 2>/dev/null | grep "^  " | awk '{print $2}' | sort -u)
        for dep in $deps; do
            apt-get download $dep 2>/dev/null || true
        done
    fi
done

cd ../..

echo ""
echo "[2/4] 收集 Python 依赖..."

mkdir -p "$OUTPUT_DIR/pip_packages"

# 获取已安装的 pip 包列表
pip3 list --format=freeze > "$OUTPUT_DIR/requirements.txt"

# 下载这些包
pip3 download -r "$OUTPUT_DIR/requirements.txt" -d "$OUTPUT_DIR/pip_packages" --no-deps 2>/dev/null || \
    pip3 download pyinstaller pillow python-xlib six altgraph packaging setuptools pyinstaller-hooks-contrib -d "$OUTPUT_DIR/pip_packages"

echo ""
echo "[3/4] 复制程序文件..."

# 复制服务端源码
cp uos_server.py "$OUTPUT_DIR/"
cp test_uos_server.py "$OUTPUT_DIR/" 2>/dev/null || true

# 创建离线安装脚本
cat > "$OUTPUT_DIR/install_offline.sh" << 'EOF'
#!/bin/bash
# UOS 远程服务端 - 离线安装脚本

set -e

echo "=========================================="
echo "UOS 远程服务端 - 离线安装"
echo "=========================================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "[1/3] 安装系统依赖..."
cd "$SCRIPT_DIR/debs"

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
echo "[2/3] 安装 Python 依赖..."
cd "$SCRIPT_DIR/pip_packages"

if ls *.whl *.tar.gz 1> /dev/null 2>&1; then
    pip3 install --no-index --find-links . pyinstaller pillow python-xlib six altgraph packaging setuptools pyinstaller-hooks-contrib
else
    echo "  警告: 未找到 Python 包"
fi

echo ""
echo "[3/3] 安装服务端..."
mkdir -p ~/uos_remote_server
cp "$SCRIPT_DIR/uos_server.py" ~/uos_remote_server/
cp "$SCRIPT_DIR/test_uos_server.py" ~/uos_remote_server/ 2>/dev/null || true

echo ""
echo "=========================================="
echo "安装完成!"
echo "=========================================="
echo ""
echo "运行方式:"
echo "  cd ~/uos_remote_server"
echo "  python3 uos_server.py"
echo ""
EOF

chmod +x "$OUTPUT_DIR/install_offline.sh"

# 创建 README
cat > "$OUTPUT_DIR/README.txt" << EOF
UOS 远程服务端 - 离线安装包
================================

打包日期: $(date +%Y-%m-%d)
架构: $(dpkg --print-architecture)

【文件说明】
- debs/: 系统依赖包 (.deb)
- pip_packages/: Python 依赖包
- uos_server.py: 服务端主程序
- install_offline.sh: 安装脚本
- requirements.txt: Python 依赖列表

【使用方法】
1. 将整个目录复制到离线 UOS 机器
2. 进入目录，运行: ./install_offline.sh
3. 安装完成后，运行: cd ~/uos_remote_server && python3 uos_server.py

【系统要求】
- UOS/Debian/Ubuntu 系统
- $(dpkg --print-architecture) 架构
- 需要 sudo 权限
EOF

echo ""
echo "[4/4] 打包..."

cd "$(dirname "$OUTPUT_DIR")"
tar -czf "${OUTPUT_DIR}.tar.gz" "$(basename "$OUTPUT_DIR")"

echo ""
echo "=========================================="
echo "打包完成!"
echo "=========================================="
echo ""
echo "输出文件: ${OUTPUT_DIR}.tar.gz"
echo ""
echo "使用方法:"
echo "1. 将 ${OUTPUT_DIR}.tar.gz 复制到离线 UOS 机器"
echo "2. 解压: tar -xzf ${OUTPUT_DIR}.tar.gz"
echo "3. 进入目录: cd $OUTPUT_DIR"
echo "4. 运行安装: ./install_offline.sh"
echo ""
