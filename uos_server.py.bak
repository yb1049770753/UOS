# -*- coding: utf-8 -*-
import socket, os, threading, io, time, sys
import tkinter as tk
from tkinter import messagebox
from PIL import ImageGrab

class UOSServerGUI:
    def __init__(self):
        # 1. 初始化 GUI 窗口
        self.root = tk.Tk()
        self.root.title("UOS 远程控制服务端")
        self.root.geometry("350x250")
        
        # 2. 状态显示
        self.status_label = tk.Label(self.root, text="🚀 服务已启动", fg="green", font=("微软雅黑", 12, "bold"))
        self.status_label.pack(pady=15)

        self.info_frame = tk.Frame(self.root)
        self.info_frame.pack(pady=5)
        
        tk.Label(self.info_frame, text="监听端口: 8888 (指令), 9999 (画面)", font=("微软雅黑", 9)).pack()
        tk.Label(self.info_frame, text="保存路径: 桌面 (Desktop)", font=("微软雅黑", 9)).pack()

        # 3. 操作按钮
        self.stop_btn = tk.Button(self.root, text="停止服务并退出", command=self.on_closing, 
                                 bg="#ff4d4f", fg="white", relief=tk.FLAT, width=20, height=2)
        self.stop_btn.pack(pady=25)

        self.is_running = True
        
        # 4. 允许远程控制权限
        os.system("xhost +local:all > /dev/null 2>&1")
        
        # 5. 启动后台处理线程
        threading.Thread(target=self.handle_commands, daemon=True).start()
        threading.Thread(target=self.start_screen_server, daemon=True).start()
        
        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        """安全退出函数"""
        if messagebox.askokcancel("退出确认", "确定要停止远程服务吗？"):
            self.is_running = False
            self.root.destroy()
            os._exit(0) # 强制结束所有守护线程

    def handle_commands(self):
        """指令处理线程 (处理键盘鼠标和文件)"""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', 8888))
        server.listen(5)
        while self.is_running:
            try:
                conn, addr = server.accept()
                while self.is_running:
                    data = conn.recv(1024)
                    if not data: break
                    lines = data.decode('utf-8', errors='ignore').strip().split('\n')
                    for line_str in lines:
                        if not line_str or ',' not in line_str: continue
                        
                        # A. 处理文件传输
                        if line_str.startswith("file_send"):
                            try:
                                _, filename, filesize = line_str.split(',')
                                save_path = os.path.join(os.path.expanduser("~"), "Desktop", filename)
                                with open(save_path, 'wb') as wf:
                                    remaining = int(filesize)
                                    while remaining > 0:
                                        chunk = conn.recv(min(remaining, 4096))
                                        if not chunk: break
                                        wf.write(chunk)
                                        remaining -= len(chunk)
                                print(f"文件已存至桌面: {filename}")
                            except: pass
                            continue
                        
                        # B. 处理键盘鼠标
                        try:
                            action, value = line_str.split(',', 1)
                            if action == 'type':
                                # 使用双引号包裹，支持空格和特殊符号
                                cmd = f'DISPLAY=:0 xdotool type --delay 0 "{value}"'
                            elif action == 'mousemove':
                                cmd = f"DISPLAY=:0 xdotool mousemove {value.replace(',', ' ')}"
                            else:
                                cmd = f"DISPLAY=:0 xdotool {action} --clearmodifiers {value}"
                            os.system(cmd)
                        except: pass
                conn.close()
            except: pass

    def start_screen_server(self):
        """画面传输线程"""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', 9999))
        server.listen(5)
        while self.is_running:
            try:
                conn, addr = server.accept()
                while self.is_running:
                    # 截图并压缩
                    img = ImageGrab.grab()
                    buf = io.BytesIO()
                    img.save(buf, format='JPEG', quality=80) 
                    data = buf.getvalue()
                    # 发送长度头(16字节) + 数据
                    conn.sendall(str(len(data)).ljust(16).encode() + data)
                    time.sleep(0.04) # 约 25 帧/秒
                conn.close()
            except: pass

if __name__ == "__main__":
    app = UOSServerGUI()
    app.root.mainloop()