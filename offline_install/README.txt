UOS 远程服务端 - 纯离线安装方案
================================

【使用步骤】

第一步：在联网机器上下载依赖包
--------------------------------
1. 找一台能联网的 Debian/UOS/Ubuntu 机器（架构要一致，都是 AMD64）
2. 复制本目录到该机器
3. 运行下载脚本：
   
   chmod +x download_packages.sh
   ./download_packages.sh

4. 下载完成后，会生成 offline_packages_YYYYMMDD 目录


第二步：复制到离线机器
----------------------
1. 将 offline_packages_YYYYMMDD 目录复制到离线 UOS 机器
2. 同时复制 uos_server.py 和 test_uos_server.py 到同一目录


第三步：在离线机器上安装
------------------------
1. 进入 offline_packages_YYYYMMDD 目录
2. 运行安装脚本：
   
   chmod +x install_offline.sh
   ./install_offline.sh

3. 安装完成后，服务端脚本会在 ~/uos_remote_server/


第四步：运行服务端
------------------
方法1 - 直接运行 Python：
   cd ~/uos_remote_server
   python3 uos_server.py

方法2 - 构建独立可执行文件（推荐）：
   cd ~/uos_remote_server
   pyinstaller --onefile --name uos_server uos_server.py
   ./uos_server


【包含的依赖包】
- python3, python3-pip, python3-dev
- python3-tk (GUI 必需)
- python3-xlib (截图备用方案)
- scrot (截图工具)
- imagemagick (截图工具)
- xdotool (鼠标键盘控制)
- xclip (剪贴板)
- 各种 X11 库文件
- pyinstaller, pillow, python-xlib (Python 包)


【注意事项】
1. 联网机器和离线机器的架构必须一致（都是 x86_64/AMD64）
2. 如果架构不同（如 ARM64），需要在对应架构的机器上重新下载
3. UOS 系统版本建议一致（如都是 UOS 20 或 UOS 21）
