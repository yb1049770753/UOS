import sys, os, socket, threading, time, queue, ctypes
from tkinter import filedialog, messagebox, simpledialog

# 保持环境路径配置
site_packages_path = r'c:\users\10497\appdata\local\programs\python\python38\lib\site-packages'
if site_packages_path not in sys.path: sys.path.append(site_packages_path)
import cv2, numpy as np, tkinter as tk
from PIL import Image, ImageTk

UOS_REAL_W, UOS_REAL_H = 1920, 1080

class RemoteClient:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw() 
        
        self.uos_ip = simpledialog.askstring("连接配置", "请输入 UOS 服务端 IP:", initialvalue="10.10.2.28")
        if not self.uos_ip:
            self.root.destroy(); return

        self.root.deiconify()
        self.root.title(f"远程全功能终端 - {self.uos_ip}")
        self.root.geometry("1280x850")

        # --- 核心：焦点监控与输入法强制锁死 ---
        self.root.bind("<FocusIn>", self.force_disable_ime)
        self.root.after(500, self.force_disable_ime)
        
        # --- 布局：工具栏 (必须先 pack) ---
        self.ctrl_bar = tk.Frame(self.root, bg="#eeeeee", height=40)
        self.ctrl_bar.pack(side=tk.TOP, fill=tk.X)
        
        tk.Button(self.ctrl_bar, text="⌨️ 切换 UOS 输入法", command=lambda: self.send_cmd("key", "ctrl+space"), bg="#e8f5e9").pack(side=tk.LEFT, padx=5, pady=5)
        tk.Button(self.ctrl_bar, text="📁 传文件", command=self.upload_file, bg="#e3f2fd").pack(side=tk.LEFT, padx=5, pady=5)
        # 补全重置按钮
        tk.Button(self.ctrl_bar, text="🔄 重置(ESC)", command=lambda: self.send_cmd("key", "Escape"), bg="#fff1f0").pack(side=tk.LEFT, padx=5, pady=5)

        # --- 布局：画布 (后 pack，填充剩余空间) ---
        self.canvas = tk.Canvas(self.root, bg='#1a1a1a', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.image_id, self.img_queue = None, queue.Queue(maxsize=2)
        
        try:
            self.cmd_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.cmd_sock.connect((self.uos_ip, 8888))
            self.img_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.img_sock.connect((self.uos_ip, 9999))
        except Exception as e:
            messagebox.showerror("连接失败", f"{e}")
            self.root.destroy(); return

        self.canvas.bind("<ButtonPress-1>", lambda e: self.send_cmd("mousedown", "1"))
        self.canvas.bind("<ButtonRelease-1>", lambda e: self.send_cmd("mouseup", "1"))
        self.canvas.bind("<Button-3>", lambda e: self.send_cmd("click", "3"))
        self.canvas.bind("<Motion>", self.on_move)
        self.canvas.bind("<B1-Motion>", self.on_move)
        self.canvas.bind("<MouseWheel>", self.on_wheel)
        self.root.bind("<Key>", self.on_key) 

        self.is_running = True
        threading.Thread(target=self.receive_loop, daemon=True).start()
        self.update_loop()
        self.root.mainloop()

    def force_disable_ime(self, event=None):
        try:
            hwnd = self.root.winfo_id()
            h_imc = ctypes.windll.imm32.ImmGetContext(hwnd)
            if h_imc:
                ctypes.windll.imm32.ImmSetOpenStatus(h_imc, 0) 
                ctypes.windll.imm32.ImmReleaseContext(hwnd, h_imc)
            ctypes.windll.imm32.ImmAssociateContext(hwnd, None)
        except: pass

    def send_cmd(self, action, value):
        try: self.cmd_sock.sendall(f"{action},{value}\n".encode())
        except: pass

    def on_key(self, e):
        ks, char = e.keysym, e.char
        low_ks = ks.lower()
        is_ctrl = e.state & 0x0004
        is_shift = e.state & 0x0001
        is_caps = e.state & 0x0002

        if ks == 'Process': return "break"

        # 1. Shift 单键
        if ks in ['Shift_L', 'Shift_R']:
            self.send_cmd("key", "shift")
            return "break"

        # 2. Ctrl 组合键
        if is_ctrl:
            if low_ks == 'space': self.send_cmd("key", "ctrl+space")
            elif len(low_ks) == 1: self.send_cmd("key", f"ctrl+{low_ks}")
            return "break"

        # 3. 特殊键
        spec = {'Up':'Up','Down':'Down','Left':'Left','Right':'Right','Return':'Return',
                'BackSpace':'BackSpace', 'Tab':'Tab', 'Escape':'Escape', 'space':'space',
                'Delete':'Delete', 'Home':'Home', 'End':'End', 'Prior':'Page_Up', 'Next':'Page_Down'}
        if ks in spec:
            self.send_cmd("key", f"{'shift+' if is_shift else ''}{spec[ks]}")
            return "break"

        # 4. 符号增强映射
        symbol_map = {
            'comma': ',', 'period': '.', 'slash': '/', 'semicolon': ';', 'apostrophe': "'",
            'bracketleft': '[', 'bracketright': ']', 'backslash': '\\', 'grave': '`',
            'minus': '-', 'equal': '=', 'question': '?', 'quotedbl': '"', 'colon': ':',
            'less': '<', 'greater': '>', 'braceleft': '{', 'braceright': '}', 'bar': '|',
            'underscore': '_', 'plus': '+', 'exclam': '!', 'at': '@', 'numbersign': '#',
            'dollar': '$', 'percent': '%', 'asciicircum': '^', 'ampersand': '&',
            'asterisk': '*', 'parenleft': '(', 'parenright': ')'
        }
        target_char = symbol_map.get(low_ks) or (char if char and char.isprintable() and not char.isalnum() else None)
        
        if target_char:
            if not (len(ks) == 1 and ks.isalpha()):
                self.send_cmd("type", target_char)
                return "break"

        # 5. 字母逻辑
        if len(ks) == 1 and ks.isalpha():
            if (is_shift and not is_caps) or (is_caps and not is_shift):
                self.send_cmd("key", f"shift+{low_ks}")
            else:
                self.send_cmd("key", low_ks)
            return "break"
        
        if len(ks) == 1:
            self.send_cmd("key", ks)
            return "break"

    def upload_file(self):
        f_path = filedialog.askopenfilename()
        if not f_path: return
        fname = os.path.basename(f_path); fsize = os.path.getsize(f_path)
        self.cmd_sock.sendall(f"file_send,{fname},{fsize}\n".encode())
        def s_t():
            with open(f_path, 'rb') as f:
                while True:
                    c = f.read(4096)
                    if not c: break
                    self.cmd_sock.sendall(c)
        threading.Thread(target=s_t).start()

    def on_move(self, e):
        if not hasattr(self, '_l'): self._l = 0
        if time.time() - self._l > 0.04:
            cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
            if cw < 1: return
            rx, ry = int(e.x * UOS_REAL_W / cw), int(e.y * UOS_REAL_H / ch)
            self.send_cmd("mousemove", f"{rx} {ry}")
            self._l = time.time()

    def on_wheel(self, e):
        self.send_cmd("click", "4" if e.delta > 0 else "5")

    def update_loop(self):
        try:
            while not self.img_queue.empty():
                img = self.img_queue.get_nowait()
                self.photo = ImageTk.PhotoImage(image=img)
                if self.image_id is None: self.image_id = self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
                else: self.canvas.itemconfig(self.image_id, image=self.photo)
        except: pass
        if self.is_running: self.root.after(20, self.update_loop)

    def receive_loop(self):
        while self.is_running:
            try:
                h = b''
                while len(h) < 16:
                    c = self.img_sock.recv(16 - len(h)); h += c
                size = int(h.strip()); b_data = b''
                while len(b_data) < size:
                    chunk = self.img_sock.recv(min(size - len(b_data), 32768)); b_data += chunk
                nparr = np.frombuffer(b_data, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if frame is not None:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pil_img = Image.fromarray(frame)
                    cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
                    if cw > 10: pil_img = pil_img.resize((cw, ch), Image.Resampling.LANCZOS)
                    if self.img_queue.full(): self.img_queue.get_nowait()
                    self.img_queue.put(pil_img)
            except: break

if __name__ == "__main__": RemoteClient()