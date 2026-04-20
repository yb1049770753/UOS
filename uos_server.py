# -*- coding: utf-8 -*-
import socket
import os
import threading
import io
import time
import sys
import subprocess
import json
import random
import string
import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image

# Linux截图函数 - 兼容UOS
_screenshot_method = None  # 缓存可用的截图方�?
_temp_dir = None

def _detect_screenshot_method():
    """检测系统可用的截图方法"""
    global _screenshot_method, _temp_dir
    import tempfile
    _temp_dir = tempfile.gettempdir()
    
    methods = [
        ('scrot', 'scrot'),
        ('import', 'import'),
        ('gnome-screenshot', 'gnome'),
        ('deepin-screenshot', 'deepin'),
        ('xwd', 'xwd'),
        ('xdg-screenshot', 'xdg'),
    ]
    
    for cmd, method_name in methods:
        try:
            r = subprocess.run(['which', cmd], capture_output=True, timeout=2)
            if r.returncode == 0:
                _screenshot_method = method_name
                print(f"[截图] 使用 {cmd}")
                return
        except:
            pass
    
    # 尝试使用 Python Xlib
    try:
        from Xlib.display import Display
        _screenshot_method = 'python-xlib'
        print("[截图] 使用 python-xlib")
        return
    except:
        pass
    
    _screenshot_method = 'none'
    print("[截图] 警告: 未找到任何截图工�?)


def linux_screenshot(bbox=None):
    """Linux截图，兼容UOS系统"""
    global _screenshot_method
    
    if _screenshot_method is None:
        _detect_screenshot_method()
    
    env = {**os.environ, 'DISPLAY': ':0'}
    method = _screenshot_method
    tmp = os.path.join(_temp_dir, f'uos_scr_{os.getpid()}.png')
    
    try:
        if method == 'scrot':
            subprocess.run(['scrot', '-o', tmp], capture_output=True, timeout=3, env=env)
        
        elif method == 'import':
            subprocess.run(['import', '-window', 'root', '-quality', '1', tmp],
                         capture_output=True, timeout=3, env=env)
        
        elif method == 'gnome':
            subprocess.run(['gnome-screenshot', '-f', tmp],
                         capture_output=True, timeout=3, env=env)
        
        elif method == 'deepin':
            subprocess.run(['deepin-screenshot', '-s', tmp],
                         capture_output=True, timeout=3, env=env)
        
        elif method == 'xwd':
            xwd_result = subprocess.run(['xwd', '-root', '-silent'],
                                        capture_output=True, timeout=3, env=env)
            if xwd_result.returncode == 0:
                convert_result = subprocess.run(['convert', 'xwd:-', tmp],
                                                input=xwd_result.stdout,
                                                capture_output=True, timeout=3)
        
        elif method == 'python-xlib':
            from Xlib.display import Display
            from Xlib import X
            display = Display(':0')
            screen = display.screen()
            geom = screen.root.get_geometry()
            raw = screen.root.get_image(0, 0, geom.width, geom.height, X.ZPixmap, 0xffffffff)
            img = Image.frombytes('RGB', (geom.width, geom.height), raw.data, 'raw', 'BGRX')
            if bbox:
                img = img.crop(bbox)
            return img
        
        # 检查截图文�?
        if os.path.exists(tmp) and os.path.getsize(tmp) > 100:
            img = Image.open(tmp)
            if bbox:
                img = img.crop(bbox)
            return img.convert('RGB')
            
    except Exception as e:
        print(f"[截图错误] {method}: {e}")
    
    # 返回空图
    return Image.new('RGB', (1, 1), (0, 0, 0))


class UOSServerGUI:
    def __init__(self):
        # 初始化配�?
        self.cmd_port = 8888
        self.screen_port = 9999
        self.password = self.generate_password()
        self.is_running = True
        self.current_screen = "primary"  # primary, secondary, all
        self.screens_info = []
        self.quality = 80  # 画质 30-95
        
        # 获取屏幕信息
        self.detect_screens()
        
        # 获取IP地址
        self.local_ip = self.get_local_ip()
        
        # 初始化GUI
        self.setup_ui()
        
        # 允许远程控制权限（如果xhost可用�?
        try:
            subprocess.run(["xhost", "+local:"], capture_output=True, timeout=2)
        except:
            pass
        
        # 启动后台线程
        threading.Thread(target=self.handle_commands, daemon=True).start()
        threading.Thread(target=self.start_screen_server, daemon=True).start()
        
        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def generate_password(self):
        """生成随机连接密码"""
        return ''.join(random.choices(string.digits, k=6))
    
    def get_local_ip(self):
        """获取本机IP地址"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    def detect_screens(self):
        """检测屏幕配�?""
        try:
            # 使用 xrandr 获取屏幕信息
            result = subprocess.run(['xrandr', '--listmonitors'], 
                                  capture_output=True, text=True)
            lines = result.stdout.strip().split('\n')
            
            self.screens_info = []
            for line in lines[1:]:  # 跳过第一�?
                if '+' in line and '*' in line:
                    # 解析屏幕信息
                    parts = line.split()
                    # 格式: 0: +*DP-1 1920/527x1080/296+0+0  DP-1
                    for i, part in enumerate(parts):
                        if 'x' in part and '+' in part:
                            # 1920/527x1080/296+0+0
                            res_part = part.split('+')[0]
                            width = int(res_part.split('x')[0].split('/')[0])
                            height = int(res_part.split('x')[1].split('/')[0])
                            
                            # 获取偏移�?
                            x_offset = int(part.split('+')[1])
                            y_offset = int(part.split('+')[2])
                            
                            is_primary = '*DP' in line or '*HDMI' in line or '*VGA' in line or '*eDP' in line
                            
                            self.screens_info.append({
                                'name': parts[-1] if len(parts) > 0 else f'Screen{len(self.screens_info)}',
                                'width': width,
                                'height': height,
                                'x': x_offset,
                                'y': y_offset,
                                'primary': is_primary or len(self.screens_info) == 0
                            })
                            break
            
            if not self.screens_info:
                # 默认单屏
                self.screens_info = [{
                    'name': 'Primary',
                    'width': 1920,
                    'height': 1080,
                    'x': 0,
                    'y': 0,
                    'primary': True
                }]
        except Exception as e:
            print(f"检测屏幕失�? {e}")
            self.screens_info = [{
                'name': 'Primary',
                'width': 1920,
                'height': 1080,
                'x': 0,
                'y': 0,
                'primary': True
            }]
    
    def get_capture_bbox(self):
        """获取当前截图区域"""
        if self.current_screen == "all" or len(self.screens_info) == 1:
            # 全屏 - 计算总区�?
            min_x = min(s['x'] for s in self.screens_info)
            min_y = min(s['y'] for s in self.screens_info)
            max_x = max(s['x'] + s['width'] for s in self.screens_info)
            max_y = max(s['y'] + s['height'] for s in self.screens_info)
            return (min_x, min_y, max_x, max_y)
        elif self.current_screen == "primary":
            # 主屏
            for s in self.screens_info:
                if s['primary']:
                    return (s['x'], s['y'], s['x'] + s['width'], s['y'] + s['height'])
            return (0, 0, 1920, 1080)
        elif self.current_screen == "secondary":
            # 副屏
            for s in self.screens_info:
                if not s['primary']:
                    return (s['x'], s['y'], s['x'] + s['width'], s['y'] + s['height'])
            # 没有副屏就用主屏
            return self.get_capture_bbox() if self.screens_info else (0, 0, 1920, 1080)
        return (0, 0, 1920, 1080)
    
    def setup_ui(self):
        """设置现代化的UI界面"""
        self.root = tk.Tk()
        self.root.title("UOS 远程控制服务�?)
        self.root.geometry("450x400")
        self.root.configure(bg='#f5f5f5')
        
        # 设置窗口居中
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - 450) // 2
        y = (screen_height - 400) // 2
        self.root.geometry(f"450x400+{x}+{y}")
        
        # 主框�?
        main_frame = tk.Frame(self.root, bg='#f5f5f5', padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = tk.Label(main_frame, text="UOS 远程控制服务�?, 
                              font=("微软雅黑", 16, "bold"), bg='#f5f5f5', fg='#333333')
        title_label.pack(pady=(0, 20))
        
        # 状态卡�?
        status_card = tk.Frame(main_frame, bg='white', relief=tk.FLAT, 
                              highlightbackground='#e0e0e0', highlightthickness=1)
        status_card.pack(fill=tk.X, pady=10, ipady=10)
        
        # 状态指示器
        status_frame = tk.Frame(status_card, bg='white')
        status_frame.pack(fill=tk.X, padx=15, pady=10)
        
        self.status_dot = tk.Label(status_frame, text="�?, font=("Arial", 14), 
                                   bg='white', fg='#52c41a')
        self.status_dot.pack(side=tk.LEFT)
        
        self.status_text = tk.Label(status_frame, text="服务运行�?, 
                                   font=("微软雅黑", 11), bg='white', fg='#52c41a')
        self.status_text.pack(side=tk.LEFT, padx=5)
        
        # IP地址显示
        ip_frame = tk.Frame(status_card, bg='white')
        ip_frame.pack(fill=tk.X, padx=15, pady=5)
        
        tk.Label(ip_frame, text="本机IP:", font=("微软雅黑", 10), 
                bg='white', fg='#666666').pack(side=tk.LEFT)
        
        ip_value = tk.Label(ip_frame, text=self.local_ip, font=("微软雅黑", 10, "bold"), 
                           bg='white', fg='#1890ff')
        ip_value.pack(side=tk.LEFT, padx=5)
        
        # 端口信息
        ports_frame = tk.Frame(status_card, bg='white')
        ports_frame.pack(fill=tk.X, padx=15, pady=5)
        
        tk.Label(ports_frame, text=f"指令端口: {self.cmd_port}  |  画面端口: {self.screen_port}", 
                font=("微软雅黑", 9), bg='white', fg='#888888').pack(side=tk.LEFT)
        
        # 连接密码
        pwd_frame = tk.Frame(main_frame, bg='#fff7e6', relief=tk.FLAT,
                            highlightbackground='#ffd591', highlightthickness=1)
        pwd_frame.pack(fill=tk.X, pady=10, ipady=10)
        
        pwd_header = tk.Frame(pwd_frame, bg='#fff7e6')
        pwd_header.pack(fill=tk.X, padx=15, pady=(10, 5))
        
        tk.Label(pwd_header, text="连接密码", font=("微软雅黑", 10, "bold"), 
                bg='#fff7e6', fg='#d46b08').pack(side=tk.LEFT)
        
        pwd_value_frame = tk.Frame(pwd_frame, bg='#fff7e6')
        pwd_value_frame.pack(fill=tk.X, padx=15, pady=5)
        
        self.pwd_label = tk.Label(pwd_value_frame, text=self.password, 
                                 font=("Consolas", 18, "bold"),
                                 bg='#fff7e6', fg='#d46b08')
        self.pwd_label.pack(side=tk.LEFT)
        
        tk.Button(pwd_value_frame, text="刷新", font=("微软雅黑", 8),
                 bg='#faad14', fg='white', relief=tk.FLAT,
                 command=self.refresh_password, cursor='hand2').pack(side=tk.LEFT, padx=10)
        
        # 屏幕选择
        if len(self.screens_info) > 1:
            screen_frame = tk.Frame(main_frame, bg='white', relief=tk.FLAT,
                                   highlightbackground='#e0e0e0', highlightthickness=1)
            screen_frame.pack(fill=tk.X, pady=10, ipady=10)
            
            tk.Label(screen_frame, text="屏幕选择", font=("微软雅黑", 10, "bold"),
                    bg='white', fg='#333333').pack(anchor='w', padx=15, pady=(10, 5))
            
            btn_frame = tk.Frame(screen_frame, bg='white')
            btn_frame.pack(fill=tk.X, padx=15, pady=5)
            
            self.screen_var = tk.StringVar(value="primary")
            
            tk.Radiobutton(btn_frame, text="主屏�?, variable=self.screen_var, 
                          value="primary", bg='white', command=self.on_screen_change).pack(side=tk.LEFT, padx=5)
            tk.Radiobutton(btn_frame, text="副屏�?, variable=self.screen_var,
                          value="secondary", bg='white', command=self.on_screen_change).pack(side=tk.LEFT, padx=5)
            tk.Radiobutton(btn_frame, text="全屏", variable=self.screen_var,
                          value="all", bg='white', command=self.on_screen_change).pack(side=tk.LEFT, padx=5)
        
        # 画质调节
        quality_frame = tk.Frame(main_frame, bg='white', relief=tk.FLAT,
                                highlightbackground='#e0e0e0', highlightthickness=1)
        quality_frame.pack(fill=tk.X, pady=10, ipady=10)
        
        tk.Label(quality_frame, text="画质调节", font=("微软雅黑", 10, "bold"),
                bg='white', fg='#333333').pack(anchor='w', padx=15, pady=(10, 5))
        
        scale_frame = tk.Frame(quality_frame, bg='white')
        scale_frame.pack(fill=tk.X, padx=15, pady=5)
        
        tk.Label(scale_frame, text="�?, font=("微软雅黑", 8), bg='white', fg='#888888').pack(side=tk.LEFT)
        
        self.quality_scale = tk.Scale(scale_frame, from_=30, to=95, orient=tk.HORIZONTAL,
                                     bg='white', highlightthickness=0, length=200,
                                     command=self.on_quality_change)
        self.quality_scale.set(self.quality)
        self.quality_scale.pack(side=tk.LEFT, padx=10)
        
        tk.Label(scale_frame, text="�?, font=("微软雅黑", 8), bg='white', fg='#888888').pack(side=tk.LEFT)
        
        self.quality_value = tk.Label(scale_frame, text=f"{self.quality}%", 
                                     font=("微软雅黑", 9), bg='white', fg='#1890ff')
        self.quality_value.pack(side=tk.LEFT, padx=10)
        
        # 停止按钮
        stop_btn = tk.Button(main_frame, text="停止服务并退�?, 
                            font=("微软雅黑", 11, "bold"),
                            bg='#ff4d4f', fg='white', relief=tk.FLAT,
                            height=2, cursor='hand2',
                            command=self.on_closing)
        stop_btn.pack(fill=tk.X, pady=(20, 0))
    
    def refresh_password(self):
        """刷新连接密码"""
        self.password = self.generate_password()
        self.pwd_label.config(text=self.password)
    
    def on_screen_change(self):
        """屏幕切换"""
        self.current_screen = self.screen_var.get()
        print(f"切换到屏�? {self.current_screen}")
    
    def on_quality_change(self, value):
        """画质调节"""
        self.quality = int(float(value))
        self.quality_value.config(text=f"{self.quality}%")
    
    def on_closing(self):
        """安全退�?""
        if messagebox.askokcancel("退出确�?, "确定要停止远程服务吗�?):
            self.is_running = False
            self.root.destroy()
            os._exit(0)
    
    def handle_commands(self):
        """指令处理线程"""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', self.cmd_port))
        server.listen(5)
        
        while self.is_running:
            try:
                conn, addr = server.accept()
                threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True).start()
            except:
                pass
    
    def handle_client(self, conn, addr):
        """处理单个客户端连�?""
        authenticated = False
        
        while self.is_running:
            try:
                data = conn.recv(1024)
                if not data:
                    break
                
                lines = data.decode('utf-8', errors='ignore').strip().split('\n')
                for line_str in lines:
                    if not line_str:
                        continue
                    
                    # 密码验证
                    if line_str.startswith("auth,"):
                        _, pwd = line_str.split(',', 1)
                        if pwd == self.password:
                            authenticated = True
                            conn.sendall(b"auth_ok\n")
                            # 发送屏幕信�?
                            screen_info = json.dumps({
                                'screens': self.screens_info,
                                'current': self.current_screen
                            })
                            conn.sendall(f"screen_info,{screen_info}\n".encode())
                        else:
                            conn.sendall(b"auth_fail\n")
                        continue
                    
                    if not authenticated:
                        conn.sendall(b"need_auth\n")
                        continue
                    
                    # 屏幕切换指令
                    if line_str.startswith("screen,"):
                        _, screen_id = line_str.split(',', 1)
                        self.current_screen = screen_id
                        if hasattr(self, 'screen_var'):
                            self.screen_var.set(screen_id)
                        continue
                    
                    # 画质调节
                    if line_str.startswith("quality,"):
                        _, q = line_str.split(',', 1)
                        self.quality = int(q)
                        if hasattr(self, 'quality_scale'):
                            self.quality_scale.set(self.quality)
                        continue
                    
                    # 文件传输
                    if line_str.startswith("file_send,"):
                        self.handle_file_receive(conn, line_str)
                        continue
                    
                    # 剪贴板同�?
                    if line_str.startswith("clipboard,"):
                        _, content = line_str.split(',', 1)
                        self.set_clipboard(content)
                        continue
                    
                    # 键盘鼠标控制
                    self.handle_input(line_str)
                    
            except Exception as e:
                print(f"客户端处理错�? {e}")
                break
        
        conn.close()
    
    def handle_file_receive(self, conn, line_str):
        """接收文件"""
        try:
            _, filename, filesize = line_str.split(',')
            save_path = os.path.join(os.path.expanduser("~"), "Desktop", filename)
            
            # 处理重名文件
            base, ext = os.path.splitext(save_path)
            counter = 1
            while os.path.exists(save_path):
                save_path = f"{base}_{counter}{ext}"
                counter += 1
            
            with open(save_path, 'wb') as wf:
                remaining = int(filesize)
                while remaining > 0:
                    chunk = conn.recv(min(remaining, 4096))
                    if not chunk:
                        break
                    wf.write(chunk)
                    remaining -= len(chunk)
            
            print(f"文件已保�? {save_path}")
        except Exception as e:
            print(f"文件接收错误: {e}")
    
    def set_clipboard(self, content):
        """设置剪贴板内�?""
        try:
            # 使用 xclip �?xsel
            os.system(f'echo "{content}" | xclip -selection clipboard')
        except:
            pass
    
    def handle_input(self, line_str):
        """处理键盘鼠标输入"""
        try:
            if ',' not in line_str:
                return
            
            action, value = line_str.split(',', 1)
            
            # 坐标转换（考虑屏幕偏移�?
            if action == 'mousemove':
                x, y = map(int, value.split())
                bbox = self.get_capture_bbox()
                # 转换到绝对坐�?
                abs_x = bbox[0] + x
                abs_y = bbox[1] + y
                cmd = f"DISPLAY=:0 xdotool mousemove {abs_x} {abs_y}"
                os.system(cmd)
            
            elif action == 'type':
                # 处理特殊字符转义
                escaped = value.replace('"', '\\"').replace('$', '\\$').replace('`', '\\`')
                cmd = f'DISPLAY=:0 xdotool type --delay 0 "{escaped}"'
                os.system(cmd)
            
            elif action == 'key':
                # 处理组合键，�?ctrl+space, shift+a �?
                if '+' in value:
                    # 组合键需要同时按下多个键
                    keys = value.split('+')
                    key_args = ' '.join(keys)
                    cmd = f"DISPLAY=:0 xdotool key {key_args}"
                else:
                    # 单键
                    cmd = f"DISPLAY=:0 xdotool key {value}"
                os.system(cmd)
            
            elif action in ['mousedown', 'mouseup', 'click']:
                cmd = f"DISPLAY=:0 xdotool {action} {value}"
                os.system(cmd)
            
        except Exception as e:
            print(f"输入处理错误: {e}")
    
    def start_screen_server(self):
        """画面传输线程"""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', self.screen_port))
        server.listen(5)
        
        while self.is_running:
            try:
                conn, addr = server.accept()
                threading.Thread(target=self.handle_screen, args=(conn,), daemon=True).start()
            except:
                pass
    
    def handle_screen(self, conn):
        """处理画面传输"""
        while self.is_running:
            try:
                bbox = self.get_capture_bbox()
                img = linux_screenshot(bbox=bbox)
                
                buf = io.BytesIO()
                img.save(buf, format='JPEG', quality=self.quality)
                data = buf.getvalue()
                
                # 发送长度头(16字节) + 数据
                conn.sendall(str(len(data)).ljust(16).encode() + data)
                time.sleep(0.04)  # �?25 �?�?
            except:
                break
        conn.close()


if __name__ == "__main__":
    # 启动日志
    log_file = os.path.expanduser("~/uos_server_debug.log")
    with open(log_file, "w") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] UOS Server starting...\n")
        f.write(f"Python: {sys.version}\n")
        f.write(f"Platform: {sys.platform}\n")
        f.write(f"Args: {sys.argv}\n")
        f.flush()
        
        try:
            # 检�?DISPLAY 环境变量
            display = os.environ.get('DISPLAY', 'NOT SET')
            f.write(f"DISPLAY: {display}\n")
            f.flush()
            
            # 初始�?tkinter
            f.write("Initializing tkinter...\n")
            f.flush()
            root = tk.Tk()
            f.write("tkinter initialized OK\n")
            f.flush()
            root.destroy()
            
            f.write("Creating UOSServerGUI...\n")
            f.flush()
            app = UOSServerGUI()
            f.write("UOSServerGUI created OK, starting mainloop\n")
            f.flush()
            app.root.mainloop()
        except Exception as e:
            import traceback
            error_msg = f"Error: {e}\n{traceback.format_exc()}"
            f.write(error_msg)
            f.flush()
            try:
                root = tk.Tk()
                root.withdraw()
                messagebox.showerror("程序错误", f"UOS远程服务端启动失�?\n{e}\n\n{traceback.format_exc()}")
            except:
                print(f"Fatal error: {e}")
                traceback.print_exc()
