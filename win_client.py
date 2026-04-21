# -*- coding: utf-8 -*-
import sys
import os
import socket
import threading
import time
import queue
import ctypes
import json
import pickle
from tkinter import filedialog, messagebox, simpledialog, ttk
import tkinter as tk
from PIL import Image, ImageTk

# Config file path
CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".uos_remote_config.pkl")


class RemoteClient:
    def __init__(self):
        self.root = tk.Tk()
        
        # 加载配置
        self.config = self.load_config()
        
        # 连接参数
        self.uos_ip = None
        self.password = None
        self.cmd_sock = None
        self.img_sock = None
        self.is_running = False
        self.authenticated = False
        
        # 屏幕信息
        self.screens_info = []
        self.current_screen = "primary"
        self.screen_width = 1920
        self.screen_height = 1080
        
        # 显示相关
        self.image_id = None
        self.img_queue = queue.Queue(maxsize=2)
        self.fullscreen = False
        self.quality = 80
        
        # 文件传输
        self.transfer_queue = queue.Queue()
        
        # 剪贴板监控
        self.last_clipboard = ""
        self.clipboard_monitor_running = False
        
        # 历史记录
        self.history_ips = self.config.get('history_ips', [])
        
        # 显示连接对话框（直接用主窗口）
        self.connected = False
        self.show_connect_dialog()
        
        # 启动主循环
        self.root.mainloop()
    
    def on_connect_success(self):
        """连接成功后切换到远程控制界面"""
        # 清空连接界面
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # 设置UI
        self.setup_ui()
        
        # 启动线程
        self.is_running = True
        threading.Thread(target=self.receive_loop, daemon=True).start()
        threading.Thread(target=self.transfer_worker, daemon=True).start()
        threading.Thread(target=self.clipboard_monitor, daemon=True).start()
        
        self.update_loop()
    
    def load_config(self):
        """加载配置"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'rb') as f:
                    return pickle.load(f)
        except:
            pass
        return {}
    
    def save_config(self):
        """保存配置"""
        try:
            with open(CONFIG_FILE, 'wb') as f:
                pickle.dump(self.config, f)
        except:
            pass
    
    def show_connect_dialog(self):
        """显示连接对话框 - 直接在主窗口上"""
        self.root.title("UOS 远程连接器")
        self.root.geometry("400x300")
        self.root.resizable(False, False)
        
        # 居中
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - 400) // 2
        y = (self.root.winfo_screenheight() - 300) // 2
        self.root.geometry(f"400x300+{x}+{y}")
        
        # 标题
        tk.Label(self.root, text="UOS 远程连接器", 
                font=("微软雅黑", 16, "bold")).pack(pady=20)
        
        # IP输入
        ip_frame = tk.Frame(self.root)
        ip_frame.pack(fill=tk.X, padx=40, pady=5)
        
        tk.Label(ip_frame, text="IP地址:", font=("微软雅黑", 10)).pack(anchor='w')
        
        # IP输入框，带历史记录
        ip_var = tk.StringVar()
        if self.history_ips:
            ip_var.set(self.history_ips[0])
        
        ip_combo = ttk.Combobox(ip_frame, textvariable=ip_var, font=("Consolas", 11))
        ip_combo['values'] = self.history_ips
        ip_combo.pack(fill=tk.X, pady=5)
        
        # 密码输入
        pwd_frame = tk.Frame(self.root)
        pwd_frame.pack(fill=tk.X, padx=40, pady=5)
        
        tk.Label(pwd_frame, text="连接密码:", font=("微软雅黑", 10)).pack(anchor='w')
        
        pwd_entry = tk.Entry(pwd_frame, font=("Consolas", 11), show="*")
        pwd_entry.pack(fill=tk.X, pady=5)
        
        # 状态标签
        status_label = tk.Label(self.root, text="", font=("微软雅黑", 9), fg="red")
        status_label.pack()
        
        # 按钮
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=15)
        
        def on_connect():
            self.uos_ip = ip_var.get().strip()
            self.password = pwd_entry.get().strip()
            
            if not self.uos_ip:
                status_label.config(text="请输入IP地址")
                return
            if not self.password:
                status_label.config(text="请输入连接密码")
                return
            
            # 保存到历史记录
            if self.uos_ip not in self.history_ips:
                self.history_ips.insert(0, self.uos_ip)
                self.history_ips = self.history_ips[:10]  # 最多10条
                self.config['history_ips'] = self.history_ips
                self.save_config()
            
            # 尝试连接
            status_label.config(text="正在连接...", fg="#1890ff")
            self.root.update()
            
            if self.connect():
                self.connected = True
                self.on_connect_success()
            else:
                status_label.config(text="连接失败，请检查IP和密码", fg="red")
        
        connect_btn = tk.Button(btn_frame, text="连接", font=("微软雅黑", 11), 
                 bg="#1890ff", fg="white", width=10,
                 command=on_connect)
        connect_btn.pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="退出", font=("微软雅黑", 11),
                 width=10, command=self.root.destroy).pack(side=tk.LEFT, padx=5)
        
        # 回车键连接
        self.root.bind('<Return>', lambda e: on_connect())
    
    def connect(self):
        """建立连接并认证"""
        try:
            # 连接指令端口
            self.cmd_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.cmd_sock.settimeout(10)
            self.cmd_sock.connect((self.uos_ip, 8888))
            
            # 发送密码认证
            self.cmd_sock.sendall(f"auth,{self.password}\n".encode())
            
            # 等待认证结果
            response = self.cmd_sock.recv(1024).decode().strip()
            if response != "auth_ok":
                messagebox.showerror("连接失败", "密码错误或连接被拒绝")
                return False
            
            self.authenticated = True
            
            # 接收屏幕信息
            data = self.cmd_sock.recv(4096).decode()
            if data.startswith("screen_info,"):
                info_json = data.split(',', 1)[1]
                info = json.loads(info_json)
                self.screens_info = info.get('screens', [])
                self.current_screen = info.get('current', 'primary')
                
                # 获取当前屏幕分辨率
                for screen in self.screens_info:
                    if self.current_screen == "primary" and screen.get('primary'):
                        self.screen_width = screen['width']
                        self.screen_height = screen['height']
                        break
                    elif self.current_screen == "secondary" and not screen.get('primary'):
                        self.screen_width = screen['width']
                        self.screen_height = screen['height']
                        break
                    elif self.current_screen == "all":
                        # 全屏模式使用总区域
                        self.screen_width = max(s['x'] + s['width'] for s in self.screens_info)
                        self.screen_height = max(s['y'] + s['height'] for s in self.screens_info)
                        break
            
            # 连接画面端口
            self.img_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.img_sock.settimeout(10)
            self.img_sock.connect((self.uos_ip, 9999))
            
            return True
            
        except Exception as e:
            messagebox.showerror("连接失败", f"无法连接到服务端: {e}")
            return False
    
    def setup_ui(self):
        """设置主界面"""
        self.root.deiconify()
        self.root.title(f"远程控制 - {self.uos_ip}")
        self.root.geometry("1280x850")
        
        # 强制禁用IME
        self.root.bind("<FocusIn>", self.force_disable_ime)
        self.root.after(500, self.force_disable_ime)
        
        # 工具栏
        self.setup_toolbar()
        
        # 画布
        self.setup_canvas()
        
        # 状态栏
        self.setup_statusbar()
        
        # 窗口大小变化事件
        self.root.bind("<Configure>", self.on_window_resize)
    
    def setup_toolbar(self):
        """设置工具栏"""
        self.ctrl_bar = tk.Frame(self.root, bg="#f0f0f0", height=45)
        self.ctrl_bar.pack(side=tk.TOP, fill=tk.X)
        self.ctrl_bar.pack_propagate(False)
        
        # 左侧按钮组
        left_frame = tk.Frame(self.ctrl_bar, bg="#f0f0f0")
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # 屏幕切换按钮
        if len(self.screens_info) > 1:
            self.screen_var = tk.StringVar(value=self.current_screen)
            
            tk.Button(left_frame, text="📺 主屏", font=("微软雅黑", 9),
                     bg="#e6f7ff", relief=tk.FLAT,
                     command=lambda: self.switch_screen("primary")).pack(side=tk.LEFT, padx=2, pady=5)
            
            tk.Button(left_frame, text="📺 副屏", font=("微软雅黑", 9),
                     bg="#f6ffed", relief=tk.FLAT,
                     command=lambda: self.switch_screen("secondary")).pack(side=tk.LEFT, padx=2, pady=5)
            
            tk.Button(left_frame, text="📺 全屏", font=("微软雅黑", 9),
                     bg="#fff7e6", relief=tk.FLAT,
                     command=lambda: self.switch_screen("all")).pack(side=tk.LEFT, padx=2, pady=5)
            
            ttk.Separator(left_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=8)
        
        # 文件传输按钮
        tk.Button(left_frame, text="📁 传文件", font=("微软雅黑", 9),
                 bg="#f6ffed", relief=tk.FLAT,
                 command=self.upload_files).pack(side=tk.LEFT, padx=2, pady=5)
        
        # 中间按钮组
        mid_frame = tk.Frame(self.ctrl_bar, bg="#f0f0f0")
        mid_frame.pack(side=tk.LEFT, fill=tk.Y, padx=20)
        
        tk.Button(mid_frame, text="⌨️ Ctrl+Shift 输入法", font=("微软雅黑", 9),
                 bg="#e6f7ff", relief=tk.FLAT,
                 command=lambda: self.send_cmd("key", "ctrl+shift")).pack(side=tk.LEFT, padx=2, pady=5)
        
        tk.Button(mid_frame, text="🔄 ESC", font=("微软雅黑", 9),
                 bg="#fff1f0", relief=tk.FLAT,
                 command=lambda: self.send_cmd("key", "Escape")).pack(side=tk.LEFT, padx=2, pady=5)
        
        # 画质调节
        ttk.Separator(mid_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=8)
        
        tk.Label(mid_frame, text="画质:", font=("微软雅黑", 9), bg="#f0f0f0").pack(side=tk.LEFT, padx=2)
        
        self.quality_scale = tk.Scale(mid_frame, from_=30, to=95, orient=tk.HORIZONTAL,
                                      length=100, showvalue=False, bg="#f0f0f0",
                                      highlightthickness=0, command=self.on_quality_change)
        self.quality_scale.set(self.quality)
        self.quality_scale.pack(side=tk.LEFT, padx=2)
        
        # 右侧按钮组
        right_frame = tk.Frame(self.ctrl_bar, bg="#f0f0f0")
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5)
        
        tk.Button(right_frame, text="⛶ 全屏", font=("微软雅黑", 9),
                 bg="#f9f0ff", relief=tk.FLAT,
                 command=self.toggle_fullscreen).pack(side=tk.LEFT, padx=2, pady=5)
        
        tk.Button(right_frame, text="❌ 断开", font=("微软雅黑", 9),
                 bg="#ff4d4f", fg="white", relief=tk.FLAT,
                 command=self.disconnect).pack(side=tk.LEFT, padx=2, pady=5)
    
    def setup_canvas(self):
        """设置画布"""
        self.canvas = tk.Canvas(self.root, bg='#1a1a1a', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # 鼠标事件
        self.canvas.bind("<ButtonPress-1>", lambda e: self.send_cmd("mousedown", "1"))
        self.canvas.bind("<ButtonRelease-1>", lambda e: self.send_cmd("mouseup", "1"))
        self.canvas.bind("<Button-3>", lambda e: self.send_cmd("click", "3"))
        self.canvas.bind("<Motion>", self.on_move)
        self.canvas.bind("<B1-Motion>", self.on_move)
        self.canvas.bind("<MouseWheel>", self.on_wheel)
        
        # 键盘事件
        self.root.bind("<Key>", self.on_key)
        self.canvas.focus_set()
        
        # 双击全屏
        self.canvas.bind("<Double-Button-1>", lambda e: self.toggle_fullscreen())
        
        # 粘贴
        self.root.bind("<Control-v>", self.on_paste)
        self.root.bind("<Control-V>", self.on_paste)
    
    def setup_statusbar(self):
        """设置状态栏"""
        self.status_bar = tk.Frame(self.root, bg="#f0f0f0", height=25)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_bar.pack_propagate(False)
        
        self.status_label = tk.Label(self.status_bar, text="已连接", 
                                    font=("微软雅黑", 9), bg="#f0f0f0", fg="#52c41a")
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        self.res_label = tk.Label(self.status_bar, 
                                 text=f"分辨率: {self.screen_width}x{self.screen_height}",
                                 font=("微软雅黑", 9), bg="#f0f0f0", fg="#666666")
        self.res_label.pack(side=tk.LEFT, padx=20)
        
        self.fps_label = tk.Label(self.status_bar, text="FPS: --", 
                                 font=("微软雅黑", 9), bg="#f0f0f0", fg="#666666")
        self.fps_label.pack(side=tk.RIGHT, padx=10)
    
    def switch_screen(self, screen_id):
        """切换屏幕"""
        self.current_screen = screen_id
        self.send_cmd("screen", screen_id)
        
        # 更新分辨率
        for screen in self.screens_info:
            if screen_id == "primary" and screen.get('primary'):
                self.screen_width = screen['width']
                self.screen_height = screen['height']
                break
            elif screen_id == "secondary" and not screen.get('primary'):
                self.screen_width = screen['width']
                self.screen_height = screen['height']
                break
            elif screen_id == "all":
                self.screen_width = max(s['x'] + s['width'] for s in self.screens_info)
                self.screen_height = max(s['y'] + s['height'] for s in self.screens_info)
                break
        
        self.res_label.config(text=f"分辨率: {self.screen_width}x{self.screen_height}")
    
    def upload_files(self):
        """上传多个文件"""
        files = filedialog.askopenfilenames(title="选择要传输的文件")
        if files:
            for f_path in files:
                self.transfer_queue.put(f_path)
    
    def transfer_worker(self):
        """文件传输工作线程"""
        while self.is_running:
            try:
                f_path = self.transfer_queue.get(timeout=1)
                self.send_file(f_path)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"传输错误: {e}")
    
    def send_file(self, f_path):
        """发送单个文件"""
        try:
            fname = os.path.basename(f_path)
            fsize = os.path.getsize(f_path)
            
            self.send_cmd("file_send", f"{fname},{fsize}")
            
            with open(f_path, 'rb') as f:
                while True:
                    chunk = f.read(4096)
                    if not chunk:
                        break
                    self.cmd_sock.sendall(chunk)
            
            print(f"文件发送完成: {fname}")
        except Exception as e:
            print(f"发送文件错误: {e}")
    
    def on_paste(self, event):
        """处理粘贴"""
        try:
            import win32clipboard
            win32clipboard.OpenClipboard()
            try:
                # 检查是否有文件
                if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_HDROP):
                    # 文件粘贴
                    files = win32clipboard.GetClipboardData(win32clipboard.CF_HDROP)
                    for f_path in files:
                        if os.path.isfile(f_path):
                            self.transfer_queue.put(f_path)
                elif win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                    # 文本粘贴
                    text = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                    self.send_cmd("type", text)
            finally:
                win32clipboard.CloseClipboard()
        except:
            pass
        return "break"
    
    def clipboard_monitor(self):
        """监控剪贴板变化"""
        try:
            import win32clipboard
            self.clipboard_monitor_running = True
            
            while self.is_running and self.clipboard_monitor_running:
                try:
                    win32clipboard.OpenClipboard()
                    try:
                        if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                            text = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                            if text != self.last_clipboard and len(text) < 10000:
                                self.last_clipboard = text
                                self.send_cmd("clipboard", text)
                    finally:
                        try:
                            win32clipboard.CloseClipboard()
                        except:
                            pass
                except:
                    pass
                time.sleep(0.5)
        except ImportError:
            print("win32clipboard 未安装，剪贴板同步功能不可用")
    
    def on_quality_change(self, value):
        """画质调节"""
        self.quality = int(float(value))
        self.send_cmd("quality", str(self.quality))
    
    def toggle_fullscreen(self):
        """切换全屏"""
        self.fullscreen = not self.fullscreen
        self.root.attributes("-fullscreen", self.fullscreen)
        
        if self.fullscreen:
            self.ctrl_bar.pack_forget()
            self.status_bar.pack_forget()
        else:
            self.ctrl_bar.pack(side=tk.TOP, fill=tk.X)
            self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def on_window_resize(self, event):
        """窗口大小变化"""
        # 可以在这里调整画面显示
        pass
    
    def force_disable_ime(self, event=None):
        """强制禁用输入法"""
        try:
            hwnd = self.root.winfo_id()
            h_imc = ctypes.windll.imm32.ImmGetContext(hwnd)
            if h_imc:
                ctypes.windll.imm32.ImmSetOpenStatus(h_imc, 0)
                ctypes.windll.imm32.ImmReleaseContext(hwnd, h_imc)
            ctypes.windll.imm32.ImmAssociateContext(hwnd, None)
        except:
            pass
    
    def send_cmd(self, action, value):
        """发送指令"""
        try:
            self.cmd_sock.sendall(f"{action},{value}\n".encode())
        except:
            pass
    
    def on_key(self, e):
        """键盘事件处理 - 完整键盘功能支持"""
        ks, char = e.keysym, e.char
        low_ks = ks.lower()
        is_ctrl = e.state & 0x0004
        is_shift = e.state & 0x0001
        is_caps = e.state & 0x0002
        
        if ks == 'Process':
            return "break"
        
        # 1. Ctrl+Shift 组合 - 切换输入法
        if is_ctrl and is_shift:
            self.send_cmd("key", "ctrl+shift")
            return "break"
        
        # 2. Ctrl 组合键（排除 Ctrl+Shift 已处理的情况）
        if is_ctrl:
            if low_ks == 'space':
                self.send_cmd("key", "ctrl+space")
            elif low_ks in ['c', 'v', 'x', 'z', 'a', 's', 'f', 'p']:
                # 常用 Ctrl 快捷键
                self.send_cmd("key", f"ctrl+{low_ks}")
            elif len(low_ks) == 1:
                self.send_cmd("key", f"ctrl+{low_ks}")
            return "break"
        
        # 3. Shift 组合键（用于输入上档符号）
        if is_shift:
            # Shift + 数字键/符号键输入上档符号
            shift_symbols = {
                # 数字键上档
                '1': '!', '2': '@', '3': '#', '4': '$', '5': '%',
                '6': '^', '7': '&', '8': '*', '9': '(', '0': ')',
                # 符号键上档
                'minus': '_', 'equal': '+', 
                'bracketleft': '{', 'bracketright': '}', 'backslash': '|',
                'semicolon': ':', 'apostrophe': '"',
                'comma': '<', 'period': '>', 'slash': '?',
                'grave': '~',
                # 直接符号（tkinter keysym）
                '-': '_', '=': '+', '[': '{', ']': '}', '\\': '|',
                ';': ':', "'": '"', ',': '<', '.': '>', '/': '?', '`': '~'
            }
            if ks in shift_symbols:
                self.send_cmd("type", shift_symbols[ks])
                return "break"
            # 处理 tkinter 返回的符号名称
            symbol_names = {
                'exclam': '!', 'at': '@', 'numbersign': '#', 'dollar': '$',
                'percent': '%', 'asciicircum': '^', 'ampersand': '&',
                'asterisk': '*', 'parenleft': '(', 'parenright': ')',
                'underscore': '_', 'plus': '+',
                'braceleft': '{', 'braceright': '}', 'bar': '|',
                'colon': ':', 'quotedbl': '"',
                'less': '<', 'greater': '>', 'question': '?',
                'asciitilde': '~'
            }
            if low_ks in symbol_names:
                self.send_cmd("type", symbol_names[low_ks])
                return "break"
        
        # 4. 特殊功能键
        spec_keys = {
            'Up': 'Up', 'Down': 'Down', 'Left': 'Left', 'Right': 'Right',
            'Return': 'Return', 'BackSpace': 'BackSpace', 'Tab': 'Tab',
            'Escape': 'Escape', 'space': 'space', 'Delete': 'Delete',
            'Home': 'Home', 'End': 'End', 'Prior': 'Page_Up', 'Next': 'Page_Down',
            'Insert': 'Insert', 'Pause': 'Pause', 'Scroll_Lock': 'Scroll_Lock',
            'Print': 'Print', 'Linefeed': 'Linefeed'
        }
        if ks in spec_keys:
            self.send_cmd("key", spec_keys[ks])
            return "break"
        
        # 5. F1-F12 功能键
        if ks.startswith('F') and ks[1:].isdigit():
            self.send_cmd("key", ks)
            return "break"
        
        # 6. 数字键盘
        numpad_keys = {
            'KP_0': '0', 'KP_1': '1', 'KP_2': '2', 'KP_3': '3', 'KP_4': '4',
            'KP_5': '5', 'KP_6': '6', 'KP_7': '7', 'KP_8': '8', 'KP_9': '9',
            'KP_Add': '+', 'KP_Subtract': '-', 'KP_Multiply': '*', 'KP_Divide': '/',
            'KP_Enter': 'Return', 'KP_Decimal': '.', 'KP_Equal': '='
        }
        if ks in numpad_keys:
            self.send_cmd("key", numpad_keys[ks])
            return "break"
        
        # 7. 字母键（处理 Shift 和 Caps Lock）
        if len(ks) == 1 and ks.isalpha():
            # 判断是否应该大写
            should_upper = (is_shift and not is_caps) or (is_caps and not is_shift)
            
            if should_upper:
                # 大写字母 - 使用 Shift+字母
                self.send_cmd("key", f"shift+{low_ks}")
            else:
                # 小写字母
                self.send_cmd("key", low_ks)
            return "break"
        
        # 8. 数字键（0-9）
        if len(ks) == 1 and ks.isdigit():
            self.send_cmd("type", ks)
            return "break"
        
        # 9. 符号键（直接输入，不带 Shift）
        symbol_keys = ['-', '=', '[', ']', '\\', ';', "'", ',', '.', '/', '`']
        if len(ks) == 1 and ks in symbol_keys:
            self.send_cmd("type", ks)
            return "break"
        
        # 10. 其他可打印字符
        if char and char.isprintable():
            self.send_cmd("type", char)
            return "break"
        
        # 11. 其他键直接发送
        if len(ks) == 1:
            self.send_cmd("key", ks)
            return "break"
    
    def on_move(self, e):
        """鼠标移动"""
        if not hasattr(self, '_last_move_time'):
            self._last_move_time = 0
        
        current_time = time.time()
        if current_time - self._last_move_time < 0.04:
            return
        
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        if cw < 1 or ch < 1:
            return
        
        # 计算相对坐标
        rx = int(e.x * self.screen_width / cw)
        ry = int(e.y * self.screen_height / ch)
        
        self.send_cmd("mousemove", f"{rx} {ry}")
        self._last_move_time = current_time
    
    def on_wheel(self, e):
        """鼠标滚轮"""
        self.send_cmd("click", "4" if e.delta > 0 else "5")
    
    def update_loop(self):
        """更新画面循环"""
        try:
            while not self.img_queue.empty():
                img = self.img_queue.get_nowait()
                
                # 自适应窗口大小
                cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
                if cw > 10 and ch > 10:
                    img = img.resize((cw, ch), Image.Resampling.LANCZOS)
                
                self.photo = ImageTk.PhotoImage(image=img)
                
                if self.image_id is None:
                    self.image_id = self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
                else:
                    self.canvas.itemconfig(self.image_id, image=self.photo)
        except:
            pass
        
        if self.is_running:
            self.root.after(20, self.update_loop)
    
    def receive_loop(self):
        """接收画面循环"""
        frame_count = 0
        last_fps_time = time.time()
        
        while self.is_running:
            try:
                # 读取长度头
                header = b''
                while len(header) < 16:
                    chunk = self.img_sock.recv(16 - len(header))
                    if not chunk:
                        raise ConnectionError("连接断开")
                    header += chunk
                
                size = int(header.strip())
                
                # 读取数据
                data = b''
                while len(data) < size:
                    chunk = self.img_sock.recv(min(size - len(data), 32768))
                    if not chunk:
                        raise ConnectionError("连接断开")
                    data += chunk
                
                # 解码图像
                nparr = np.frombuffer(data, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if frame is not None:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pil_img = Image.fromarray(frame)
                    
                    if self.img_queue.full():
                        self.img_queue.get_nowait()
                    self.img_queue.put(pil_img)
                    
                    # 计算FPS
                    frame_count += 1
                    current_time = time.time()
                    if current_time - last_fps_time >= 1.0:
                        fps = frame_count
                        self.fps_label.config(text=f"FPS: {fps}")
                        frame_count = 0
                        last_fps_time = current_time
                        
            except Exception as e:
                print(f"接收错误: {e}")
                self.status_label.config(text="连接断开", fg="#ff4d4f")
                break
    
    def disconnect(self):
        """断开连接"""
        if messagebox.askokcancel("确认", "确定要断开连接吗？"):
            self.is_running = False
            try:
                self.cmd_sock.close()
                self.img_sock.close()
            except:
                pass
            self.root.destroy()


if __name__ == "__main__":
    try:
        RemoteClient()
    except Exception as e:
        import traceback
        try:
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("程序错误", f"UOS远程连接器启动失败:\n{e}\n\n{traceback.format_exc()}")
        except:
            print(f"Fatal error: {e}")
            traceback.print_exc()
