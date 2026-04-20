#!/bin/bash
# UOS 远程服务端安装脚本

echo "=========================================="
echo "UOS 远程控制服务端 - 安装程序"
echo "=========================================="
echo ""

# 检查系统类型
if [ -f /etc/os-release ]; then
    . /etc/os-release
    echo "检测到系统: $NAME $VERSION_ID"
else
    echo "无法检测系统类型"
fi

echo ""
echo "检查依赖..."

# 检查 xdotool
if ! command -v xdotool &> /dev/null; then
    echo "⚠ 警告: xdotool 未安装 (鼠标键盘控制功能将不可用)"
    echo "  如需安装，请运行: sudo apt-get install xdotool"
else
    echo "✓ xdotool 已安装"
fi

# 检查截图工具
SCREENSHOT_TOOLS=""
for tool in scrot import gnome-screenshot deepin-screenshot xwd; do
    if command -v $tool &> /dev/null; then
        SCREENSHOT_TOOLS="$SCREENSHOT_TOOLS $tool"
    fi
done

if [ -z "$SCREENSHOT_TOOLS" ]; then
    echo "⚠ 警告: 未检测到截图工具"
    echo "  程序将尝试使用内置截图功能"
    echo "  建议安装: sudo apt-get install scrot"
else
    echo "✓ 截图工具: $SCREENSHOT_TOOLS"
fi

# 检查 DISPLAY
echo ""
echo "检查显示环境..."
if [ -z "$DISPLAY" ]; then
    echo "⚠ 警告: DISPLAY 环境变量未设置"
    echo "  尝试设置为 :0"
    export DISPLAY=:0
fi
echo "✓ DISPLAY=$DISPLAY"

# 创建桌面快捷方式
echo ""
read -p "是否创建桌面快捷方式? (y/n): " create_desktop
if [ "$create_desktop" = "y" ] || [ "$create_desktop" = "Y" ]; then
    DESKTOP_DIR="$HOME/Desktop"
    if [ -d "$DESKTOP_DIR" ]; then
        cat > "$DESKTOP_DIR/UOS远程服务端.desktop" << EOF
[Desktop Entry]
Name=UOS远程服务端
Comment=UOS远程控制服务端
Exec=$(pwd)/uos_server
Icon=$(pwd)/icon.png
Terminal=false
Type=Application
Categories=Network;
EOF
        chmod +x "$DESKTOP_DIR/UOS远程服务端.desktop"
        echo "✓ 桌面快捷方式已创建"
    else
        echo "✗ 未找到桌面目录"
    fi
fi

echo ""
echo "=========================================="
echo "安装完成!"
echo "=========================================="
echo ""
echo "启动方式:"
echo "  1. 双击运行 uos_server"
echo "  2. 命令行: ./uos_server"
echo ""
echo "日志文件: ~/uos_server_debug.log"
echo ""
read -p "是否立即启动? (y/n): " start_now
if [ "$start_now" = "y" ] || [ "$start_now" = "Y" ]; then
    ./uos_server
fi
