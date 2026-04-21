#!/usr/bin/env python3
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

# Linux screenshot - UOS compatible
_screenshot_method = None
_temp_dir = None

def _detect_screenshot_method():
    """Detect available screenshot method"""
    global _screenshot_method, _temp_dir
    import tempfile
    _temp_dir = tempfile.gettempdir()
    
    try:
        r = subprocess.run(['which', 'scrot'], capture_output=True, timeout=2)
        if r.returncode == 0:
            _screenshot_method = 'scrot'
            print("[Screenshot] Using scrot")
            return
    except:
        pass
    
    methods = [
        ('import', 'import'),
        ('gnome-screenshot', 'gnome'),
        ('deepin-screenshot', 'deepin'),
        ('xwd', 'xwd'),
    ]
    
    for cmd, method_name in methods:
        try:
            r = subprocess.run(['which', cmd], capture_output=True, timeout=2)
            if r.returncode == 0:
                _screenshot_method = method_name
                print(f"[Screenshot] Using {cmd}")
                return
        except:
            pass
    
    _screenshot_method = 'none'
    print("[Screenshot] Warning: No tool found")
    print("[Screenshot] Install: sudo apt-get install scrot")

def linux_screenshot(bbox=None):
    """Linux screenshot, UOS compatible"""
    global _screenshot_method
    
    if _screenshot_method is None:
        _detect_screenshot_method()
    
    env = {**os.environ, 'DISPLAY': ':0'}
    method = _screenshot_method
    tmp = os.path.join(_temp_dir, f'uos_scr_{os.getpid()}.png')
    
    try:
        if method == 'scrot':
            subprocess.run(['scrot', '-z', '-o', tmp], capture_output=True, timeout=3, env=env)
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
                subprocess.run(['convert', 'xwd:-', tmp],
                              input=xwd_result.stdout,
                              capture_output=True, timeout=3)
        
        if os.path.exists(tmp) and os.path.getsize(tmp) > 100:
            img = Image.open(tmp)
            if bbox:
                img = img.crop(bbox)
            return img.convert('RGB')
            
    except Exception as e:
        print(f"[Screenshot Error] {method}: {e}")
    
    if bbox:
        width = max(1, bbox[2] - bbox[0])
        height = max(1, bbox[3] - bbox[1])
        return Image.new('RGB', (width, height), (80, 80, 80))
    return Image.new('RGB', (1920, 1080), (80, 80, 80))


class UOSServerGUI:
    def __init__(self):
        self.cmd_port = 12138
        self.screen_port = 12139
        self.password = self.generate_password()
        self.is_running = True
        self.current_screen = "primary"
        self.screens_info = []
        self.quality = 25
        self.client_conn = None
        self.last_remote_clipboard = ""
        
        self.detect_screens()
        self.local_ip = self.get_local_ip()
        self.setup_ui()
        
        try:
            subprocess.run(["xhost", "+local:"], capture_output=True, timeout=2)
        except:
            pass
        
        threading.Thread(target=self.handle_commands, daemon=True).start()
        threading.Thread(target=self.start_screen_server, daemon=True).start()
        threading.Thread(target=self.remote_clipboard_sync, daemon=True).start()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def generate_password(self):
        return ''.join(random.choices(string.digits, k=6))
    
    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    def detect_screens(self):
        try:
            result = subprocess.run(['xrandr', '--listmonitors'], 
                                  capture_output=True, text=True)
            lines = result.stdout.strip().split('\n')
            
            self.screens_info = []
            for line in lines[1:]:
                if '+' in line and '*' in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if 'x' in part and '+' in part:
                            res_part = part.split('+')[0]
                            width = int(res_part.split('x')[0].split('/')[0])
                            height = int(res_part.split('x')[1].split('/')[0])
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
                self.screens_info = [{
                    'name': 'Primary',
                    'width': 1920,
                    'height': 1080,
                    'x': 0,
                    'y': 0,
                    'primary': True
                }]
        except Exception as e:
            print(f"Screen detect error: {e}")
            self.screens_info = [{
                'name': 'Primary',
                'width': 1920,
                'height': 1080,
                'x': 0,
                'y': 0,
                'primary': True
            }]
    
    def get_capture_bbox(self):
        if not self.screens_info:
            return (0, 0, 1920, 1080)
        
        if self.current_screen == "all":
            min_x = min(s['x'] for s in self.screens_info)
            min_y = min(s['y'] for s in self.screens_info)
            max_x = max(s['x'] + s['width'] for s in self.screens_info)
            max_y = max(s['y'] + s['height'] for s in self.screens_info)
            return (min_x, min_y, max_x, max_y)
        elif self.current_screen == "primary":
            for s in self.screens_info:
                if s.get('primary', False):
                    return (s['x'], s['y'], s['x'] + s['width'], s['y'] + s['height'])
            s = self.screens_info[0]
            return (s['x'], s['y'], s['x'] + s['width'], s['y'] + s['height'])
        elif self.current_screen == "secondary":
            for s in self.screens_info:
                if not s.get('primary', False):
                    return (s['x'], s['y'], s['x'] + s['width'], s['y'] + s['height'])
            return self.get_capture_bbox() if self.screens_info else (0, 0, 1920, 1080)
        return (0, 0, 1920, 1080)
    
    def setup_ui(self):
        self.root = tk.Tk()
        self.root.title("UOS Remote Server")
        self.root.geometry("450x400")
        self.root.configure(bg='#f5f5f5')
        
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - 450) // 2
        y = (screen_height - 400) // 2
        self.root.geometry(f"450x400+{x}+{y}")
        
        main_frame = tk.Frame(self.root, bg='#f5f5f5', padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        title_label = tk.Label(main_frame, text="UOS Remote Server", 
                              font=("Arial", 16, "bold"), bg='#f5f5f5', fg='#333333')
        title_label.pack(pady=(0, 20))
        
        status_card = tk.Frame(main_frame, bg='white', relief=tk.FLAT, 
                              highlightbackground='#e0e0e0', highlightthickness=1)
        status_card.pack(fill=tk.X, pady=10, ipady=10)
        
        status_frame = tk.Frame(status_card, bg='white')
        status_frame.pack(fill=tk.X, padx=15, pady=10)
        
        self.status_dot = tk.Label(status_frame, text="*", font=("Arial", 14), 
                                   bg='white', fg='#52c41a')
        self.status_dot.pack(side=tk.LEFT)
        
        self.status_text = tk.Label(status_frame, text="Running", 
                                   font=("Arial", 11), bg='white', fg='#52c41a')
        self.status_text.pack(side=tk.LEFT, padx=5)
        
        ip_frame = tk.Frame(status_card, bg='white')
        ip_frame.pack(fill=tk.X, padx=15, pady=5)
        
        tk.Label(ip_frame, text="IP:", font=("Arial", 10), 
                bg='white', fg='#666666').pack(side=tk.LEFT)
        
        ip_value = tk.Label(ip_frame, text=self.local_ip, font=("Arial", 10, "bold"), 
                           bg='white', fg='#1890ff')
        ip_value.pack(side=tk.LEFT, padx=5)
        
        ports_frame = tk.Frame(status_card, bg='white')
        ports_frame.pack(fill=tk.X, padx=15, pady=5)
        
        tk.Label(ports_frame, text=f"Cmd: {self.cmd_port}  |  Screen: {self.screen_port}", 
                font=("Arial", 9), bg='white', fg='#888888').pack(side=tk.LEFT)
        
        pwd_frame = tk.Frame(main_frame, bg='#fff7e6', relief=tk.FLAT,
                            highlightbackground='#ffd591', highlightthickness=1)
        pwd_frame.pack(fill=tk.X, pady=10, ipady=10)
        
        pwd_header = tk.Frame(pwd_frame, bg='#fff7e6')
        pwd_header.pack(fill=tk.X, padx=15, pady=(10, 5))
        
        tk.Label(pwd_header, text="Password", font=("Arial", 10, "bold"), 
                bg='#fff7e6', fg='#d46b08').pack(side=tk.LEFT)
        
        pwd_value_frame = tk.Frame(pwd_frame, bg='#fff7e6')
        pwd_value_frame.pack(fill=tk.X, padx=15, pady=5)
        
        self.pwd_label = tk.Label(pwd_value_frame, text=self.password, 
                                 font=("Consolas", 18, "bold"),
                                 bg='#fff7e6', fg='#d46b08')
        self.pwd_label.pack(side=tk.LEFT)
        
        tk.Button(pwd_value_frame, text="Refresh", font=("Arial", 8),
                 bg='#faad14', fg='white', relief=tk.FLAT,
                 command=self.refresh_password, cursor='hand2').pack(side=tk.LEFT, padx=10)
        
        if len(self.screens_info) > 1:
            screen_frame = tk.Frame(main_frame, bg='white', relief=tk.FLAT,
                                   highlightbackground='#e0e0e0', highlightthickness=1)
            screen_frame.pack(fill=tk.X, pady=10, ipady=10)
            
            tk.Label(screen_frame, text="Screen", font=("Arial", 10, "bold"),
                    bg='white', fg='#333333').pack(anchor='w', padx=15, pady=(10, 5))
            
            btn_frame = tk.Frame(screen_frame, bg='white')
            btn_frame.pack(fill=tk.X, padx=15, pady=5)
            
            self.screen_var = tk.StringVar(value="primary")
            
            tk.Radiobutton(btn_frame, text="Primary", variable=self.screen_var, 
                          value="primary", bg='white', command=self.on_screen_change).pack(side=tk.LEFT, padx=5)
            tk.Radiobutton(btn_frame, text="Secondary", variable=self.screen_var,
                          value="secondary", bg='white', command=self.on_screen_change).pack(side=tk.LEFT, padx=5)
            tk.Radiobutton(btn_frame, text="All", variable=self.screen_var,
                          value="all", bg='white', command=self.on_screen_change).pack(side=tk.LEFT, padx=5)
        
        quality_frame = tk.Frame(main_frame, bg='white', relief=tk.FLAT,
                                highlightbackground='#e0e0e0', highlightthickness=1)
        quality_frame.pack(fill=tk.X, pady=10, ipady=10)
        
        tk.Label(quality_frame, text="Quality", font=("Arial", 10, "bold"),
                bg='white', fg='#333333').pack(anchor='w', padx=15, pady=(10, 5))
        
        scale_frame = tk.Frame(quality_frame, bg='white')
        scale_frame.pack(fill=tk.X, padx=15, pady=5)
        
        tk.Label(scale_frame, text="Low", font=("Arial", 8), bg='white', fg='#888888').pack(side=tk.LEFT)
        
        self.quality_scale = tk.Scale(scale_frame, from_=30, to=95, orient=tk.HORIZONTAL,
                                     bg='white', highlightthickness=0, length=200,
                                     command=self.on_quality_change)
        self.quality_scale.set(self.quality)
        self.quality_scale.pack(side=tk.LEFT, padx=10)
        
        tk.Label(scale_frame, text="High", font=("Arial", 8), bg='white', fg='#888888').pack(side=tk.LEFT)
        
        self.quality_value = tk.Label(scale_frame, text=f"{self.quality}%", 
                                     font=("Arial", 9), bg='white', fg='#1890ff')
        self.quality_value.pack(side=tk.LEFT, padx=10)
        
        stop_btn = tk.Button(main_frame, text="Stop & Exit", 
                            font=("Arial", 11, "bold"),
                            bg='#ff4d4f', fg='white', relief=tk.FLAT,
                            height=2, cursor='hand2',
                            command=self.on_closing)
        stop_btn.pack(fill=tk.X, pady=(20, 0))
    
    def refresh_password(self):
        self.password = self.generate_password()
        self.pwd_label.config(text=self.password)
    
    def on_screen_change(self):
        self.current_screen = self.screen_var.get()
        print(f"Screen: {self.current_screen}")
    
    def on_quality_change(self, value):
        self.quality = int(float(value))
        self.quality_value.config(text=f"{self.quality}%")
    
    def on_closing(self):
        if messagebox.askokcancel("Exit", "Stop remote service?"):
            self.is_running = False
            self.root.destroy()
            os._exit(0)
    
    def handle_commands(self):
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
        authenticated = False
        self.client_conn = conn
        
        while self.is_running:
            try:
                data = conn.recv(1024)
                if not data:
                    break
                
                lines = data.decode('utf-8', errors='ignore').strip().split('\n')
                for line_str in lines:
                    if not line_str:
                        continue
                    
                    if line_str.startswith("auth,"):
                        _, pwd = line_str.split(',', 1)
                        if pwd == self.password:
                            authenticated = True
                            conn.sendall(b"auth_ok\n")
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
                    
                    if line_str.startswith("screen,"):
                        _, screen_id = line_str.split(',', 1)
                        self.current_screen = screen_id
                        if hasattr(self, 'screen_var'):
                            self.screen_var.set(screen_id)
                        continue
                    
                    if line_str.startswith("quality,"):
                        _, q = line_str.split(',', 1)
                        self.quality = int(q)
                        if hasattr(self, 'quality_scale'):
                            self.quality_scale.set(self.quality)
                        continue
                    
                    if line_str.startswith("file_send,"):
                        self.handle_file_receive(conn, line_str)
                        continue
                    
                    if line_str.startswith("download,"):
                        self.handle_file_send(conn, line_str)
                        continue
                    
                    if line_str.startswith("clipboard,"):
                        _, content = line_str.split(',', 1)
                        self.set_clipboard(content)
                        continue
                    
                    self.handle_input(line_str)
                    
            except Exception as e:
                print(f"Client error: {e}")
                break
        
        if self.client_conn is conn:
            self.client_conn = None
        conn.close()
    
    def remote_clipboard_sync(self):
        """UOS→Windows 剪贴板同步"""
        while self.is_running:
            try:
                if self.client_conn:
                    result = subprocess.run(
                        ['xclip', '-selection', 'clipboard', '-o'],
                        capture_output=True, text=True, timeout=2
                    )
                    if result.returncode == 0:
                        content = result.stdout
                        if content and content != self.last_remote_clipboard:
                            self.last_remote_clipboard = content
                            import base64
                            encoded = base64.b64encode(content.encode('utf-8')).decode('ascii')
                            self.client_conn.sendall(f"remote_clip,{encoded}\n".encode())
            except Exception as e:
                pass
            time.sleep(1)
    
    def handle_file_receive(self, conn, line_str):
        try:
            _, filename, filesize = line_str.split(',')
            save_path = os.path.join(os.path.expanduser("~"), "Desktop", filename)
            
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
            
            print(f"File saved: {save_path}")
        except Exception as e:
            print(f"File receive error: {e}")
    
    def handle_file_send(self, conn, line_str):
        """发送文件给客户端"""
        try:
            _, filepath = line_str.split(',', 1)
            filepath = filepath.strip()
            
            if not os.path.isfile(filepath):
                conn.sendall(f"error,文件不存在: {filepath}\n".encode())
                return
            
            fname = os.path.basename(filepath)
            fsize = os.path.getsize(filepath)
            
            conn.sendall(f"file_data,{fname},{fsize}\n".encode())
            
            with open(filepath, 'rb') as f:
                while True:
                    chunk = f.read(4096)
                    if not chunk:
                        break
                    conn.sendall(chunk)
            
            print(f"File sent: {filepath}")
        except Exception as e:
            try:
                conn.sendall(f"error,{str(e)}\n".encode())
            except:
                pass
            print(f"File send error: {e}")
    
    def set_clipboard(self, content):
        try:
            os.system(f'echo "{content}" | xclip -selection clipboard')
        except:
            pass
    
    def handle_input(self, line_str):
        try:
            if ',' not in line_str:
                return
            
            action, value = line_str.split(',', 1)
            
            if action == 'mousemove':
                x, y = map(int, value.split())
                bbox = self.get_capture_bbox()
                abs_x = bbox[0] + x
                abs_y = bbox[1] + y
                cmd = f"DISPLAY=:0 xdotool mousemove {abs_x} {abs_y}"
                os.system(cmd)
            
            elif action == 'type':
                escaped = value.replace('"', '\\"').replace('$', '\\$').replace('`', '\\`')
                cmd = f'DISPLAY=:0 xdotool type --delay 0 "{escaped}"'
                os.system(cmd)
            
            elif action == 'key':
                toggle_keys = ('Caps_Lock', 'Num_Lock', 'Scroll_Lock')
                if value in toggle_keys:
                    # Toggle键直接发送
                    cmd = f"DISPLAY=:0 xdotool key {value}"
                elif '+' in value:
                    # 组合键用 keydown/keyup 确保正确模拟
                    keys = value.split('+')
                    modifiers = ' '.join(keys[:-1])
                    main_key = keys[-1]
                    cmd = f"DISPLAY=:0 xdotool keydown {modifiers} key {main_key} keyup {modifiers}"
                else:
                    # 单键用 --clearmodifiers 避免修饰键残留干扰
                    cmd = f"DISPLAY=:0 xdotool key --clearmodifiers {value}"
                os.system(cmd)
            
            elif action == 'doubleclick':
                cmd = f"DISPLAY=:0 xdotool click --repeat 2 {value}"
                os.system(cmd)
            
            elif action in ['mousedown', 'mouseup', 'click']:
                cmd = f"DISPLAY=:0 xdotool {action} {value}"
                os.system(cmd)
            
        except Exception as e:
            print(f"Input error: {e}")
    
    def start_screen_server(self):
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
        print("[Screen] Client connected")
        frame_count = 0
        debug_saved = False
        while self.is_running:
            try:
                bbox = self.get_capture_bbox()
                print(f"[Screen] bbox={bbox}")
                img = linux_screenshot(bbox=bbox)
                print(f"[Screen] Screenshot size={img.size}, mode={img.mode}")
                
                if not debug_saved:
                    debug_path = "/tmp/uos_debug_0.png"
                    img.save(debug_path)
                    print(f"[Screen] Debug saved to {debug_path}")
                    debug_saved = True
                
                if img.width <= 1 or img.height <= 1:
                    print("[Screen] Screenshot failed, using default")
                    img = Image.new('RGB', (1920, 1080), (100, 100, 100))
                
                buf = io.BytesIO()
                img.save(buf, format='JPEG', quality=self.quality)
                data = buf.getvalue()
                
                if len(data) < 100:
                    time.sleep(0.1)
                    continue
                
                conn.sendall(str(len(data)).ljust(16).encode() + data)
                frame_count += 1
                if frame_count % 15 == 0:
                    print(f"[Screen] Sent {frame_count} frames, {len(data)} bytes, quality={self.quality}")
                time.sleep(0.1)
            except Exception as e:
                print(f"[Screen] Error: {e}")
                import traceback
                traceback.print_exc()
                break
        print(f"[Screen] Client disconnected, {frame_count} frames total")
        conn.close()


if __name__ == "__main__":
    try:
        app = UOSServerGUI()
        app.root.mainloop()
    except Exception as e:
        import traceback
        print(f"Error: {e}")
        traceback.print_exc()
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Error", f"Server start failed:\n{e}")
        except:
            pass
