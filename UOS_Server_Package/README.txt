UOS 远程控制服务端 - 离线安装包
================================

适用系统: UOS / Deepin / Debian / Ubuntu (AMD64/ARM64)

【安装步骤】
1. 解压本压缩包到任意目录
2. 进入解压后的目录
3. 双击运行: ./uos_server
   或命令行运行: ./uos_server

【依赖说明】
本包已包含所有必要的 Python 依赖和库文件，无需联网安装。

【系统要求】
- X11 显示环境 (DISPLAY=:0)
- xdotool (用于鼠标键盘控制，如未安装会提示)

【截图工具】
如果系统已安装以下任一截图工具，将自动使用：
- scrot (推荐)
- ImageMagick (import 命令)
- gnome-screenshot
- deepin-screenshot
- xwd + convert

如果没有安装任何截图工具，程序会尝试使用内置的 X11 截图功能。

【安装截图工具】
如果系统可以联网，建议安装 scrot：
  sudo apt-get install scrot

【故障排查】
如果无法启动：
1. 检查 DISPLAY 环境变量: echo $DISPLAY
2. 查看日志文件: ~/uos_server_debug.log
3. 运行诊断脚本: python3 test_uos_server.py

【文件说明】
- uos_server: 主程序 (PyInstaller 打包)
- uos_server.py: Python 源码
- test_uos_server.py: 诊断工具
