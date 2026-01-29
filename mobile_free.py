import tkinter as tk
from tkinter import messagebox, simpledialog
import socket
import threading
import json
import time
from PIL import Image, ImageTk
import io
import base64

class CameraStreamFreeApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("手機相機串流 (免費版)")
        self.root.geometry("400x600")
        
        self.is_server = False
        self.is_client = False
        self.relay_socket = None
        self.connected_peer = None
        
        self.setup_ui()
    
    def setup_ui(self):
        # 標題
        title = tk.Label(self.root, text="手機相機串流", font=("Arial", 16, "bold"))
        title.pack(pady=10)
        
        # 雲端伺服器設定
        server_frame = tk.Frame(self.root)
        server_frame.pack(pady=5)
        tk.Label(server_frame, text="雲端伺服器:").pack(side=tk.LEFT)
        self.server_entry = tk.Entry(server_frame, width=20)
        self.server_entry.insert(0, "your-server.com:9999")
        self.server_entry.pack(side=tk.LEFT)
        
        # 模式選擇
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)
        
        server_btn = tk.Button(button_frame, text="啟動舊手機\n(相機伺服器)", 
                             command=self.start_server, width=15, height=3, bg="lightblue")
        server_btn.pack(side=tk.LEFT, padx=5)
        
        client_btn = tk.Button(button_frame, text="啟動新手機\n(觀看客戶端)", 
                             command=self.start_client, width=15, height=3, bg="lightgreen")
        client_btn.pack(side=tk.LEFT, padx=5)
        
        # 狀態顯示
        self.status_label = tk.Label(self.root, text="請選擇模式", fg="blue", font=("Arial", 12))
        self.status_label.pack(pady=5)
        
        # 伺服器列表
        self.server_var = tk.StringVar()
        self.server_combo = tk.OptionMenu(self.root, self.server_var, "選擇伺服器")
        self.server_combo.pack(pady=5)
        self.server_combo.config(state="disabled")
        
        # 連接按鈕
        self.connect_btn = tk.Button(self.root, text="連接到選定伺服器", 
                                    command=self.connect_to_server, state="disabled", 
                                    bg="orange", fg="white")
        self.connect_btn.pack(pady=5)
        
        # 影像顯示區域
        self.image_label = tk.Label(self.root, text="影像顯示區域\n(等待連接)", 
                                   bg="black", fg="white", width=40, height=15)
        self.image_label.pack(pady=10)
        
        # 控制按鈕
        control_frame = tk.Frame(self.root)
        control_frame.pack(pady=5)
        
        self.record_btn = tk.Button(control_frame, text="開始錄影", 
                                  command=self.toggle_recording, state="disabled",
                                  bg="red", fg="white")
        self.record_btn.pack(side=tk.LEFT, padx=5)
        
        stop_btn = tk.Button(control_frame, text="停止", command=self.stop_app,
                           bg="gray", fg="white")
        stop_btn.pack(side=tk.LEFT, padx=5)
        
        # 說明文字
        info_text = tk.Label(self.root, 
                           text="免費版本 - 無需OpenCV\n支援跨網路連接和基本影像串流",
                           fg="gray", font=("Arial", 9))
        info_text.pack(pady=5)
    
    def connect_to_relay(self):
        """連接到雲端中轉伺服器"""
        server_info = self.server_entry.get().strip()
        if ':' not in server_info:
            self.status_label.config(text="伺服器格式錯誤", fg="red")
            return False
        
        host, port = server_info.split(':')
        try:
            port = int(port)
        except:
            self.status_label.config(text="埠號錯誤", fg="red")
            return False
        
        try:
            self.relay_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.relay_socket.connect((host, port))
            self.status_label.config(text=f"已連接到雲端伺服器", fg="green")
            
            # 啟動接收線程
            threading.Thread(target=self.receive_from_relay, daemon=True).start()
            return True
            
        except Exception as e:
            self.status_label.config(text=f"連接失敗: {str(e)}", fg="red")
            return False
    
    def start_server(self):
        """啟動舊手機相機伺服器"""
        self.is_server = True
        
        if not self.connect_to_relay():
            return
        
        # 註冊為伺服器
        register_msg = {
            'type': 'register',
            'client_type': 'server'
        }
        self.send_to_relay(register_msg)
        
        self.status_label.config(text="相機伺服器模式，等待客戶端...", fg="blue")
        self.connect_btn.config(state="normal")
        
        # 開始傳送測試影像
        threading.Thread(target=self.send_test_images, daemon=True).start()
    
    def start_client(self):
        """啟動新手機客戶端模式"""
        self.is_client = True
        
        if not self.connect_to_relay():
            return
        
        # 註冊為客戶端
        register_msg = {
            'type': 'register',
            'client_type': 'client'
        }
        self.send_to_relay(register_msg)
        
        self.status_label.config(text="客戶端模式，等待伺服器列表...", fg="blue")
        self.record_btn.config(state="normal")
    
    def send_test_images(self):
        """傳送測試影像 (不需要真實相機)"""
        import random
        
        while self.is_server and self.relay_socket and self.connected_peer:
            try:
                # 建立簡單的測試影像資料
                test_data = f"TEST_IMAGE_{int(time.time())}_{random.randint(1000, 9999)}".encode()
                
                # 傳送資料大小和內容
                size = len(test_data)
                self.relay_socket.send(size.to_bytes(4, 'big'))
                self.relay_socket.send(test_data)
                
                time.sleep(0.1)  # 模擬幀率
                
            except Exception as e:
                print(f'傳送錯誤: {e}')
                break
    
    def receive_from_relay(self):
        """接收雲端伺服器的訊息"""
        while self.relay_socket:
            try:
                data = self.relay_socket.recv(4096)
                if not data:
                    break
                
                try:
                    message = json.loads(data.decode())
                    self.process_relay_message(message)
                except json.JSONDecodeError:
                    if self.is_client:
                        self.process_test_data(data)
                        
            except Exception as e:
                print(f'接收錯誤: {e}')
                break
    
    def process_relay_message(self, message):
        """處理雲端伺服器訊息"""
        msg_type = message.get('type')
        
        if msg_type == 'registered':
            self.status_label.config(text="已註冊", fg="green")
            
        elif msg_type == 'server_list':
            servers = message.get('servers', [])
            if servers:
                self.server_combo['menu'].delete(0, 'end')
                for server in servers:
                    self.server_combo['menu'].add_command(label=server, 
                                                        command=tk._setit(self.server_var, server))
                self.server_combo.config(state="normal")
                self.connect_btn.config(state="normal")
                self.status_label.config(text=f"找到 {len(servers)} 個伺服器", fg="green")
            
        elif msg_type == 'connected':
            self.connected_peer = message.get('peer')
            self.status_label.config(text=f"已連接到 {self.connected_peer}", fg="green")
    
    def connect_to_server(self):
        """連接到選定的伺服器"""
        server = self.server_var.get()
        if server and server != "選擇伺服器":
            connect_msg = {
                'type': 'connect',
                'target': server
            }
            self.send_to_relay(connect_msg)
            self.status_label.config(text=f"正在連接到 {server}...", fg="blue")
    
    def process_test_data(self, data):
        """處理接收到的測試資料"""
        try:
            # 解析測試影像資料
            test_info = data.decode()
            
            # 更新顯示
            self.image_label.config(text=f"接收影像:\n{test_info}", fg="lime")
            
        except Exception as e:
            print(f'資料處理錯誤: {e}')
    
    def send_to_relay(self, message):
        """發送訊息到雲端伺服器"""
        if self.relay_socket:
            try:
                data = json.dumps(message).encode()
                self.relay_socket.send(data)
            except Exception as e:
                print(f'發送錯誤: {e}')
    
    def toggle_recording(self):
        """切換錄影狀態"""
        if hasattr(self, 'is_recording') and self.is_recording:
            self.is_recording = False
            self.record_btn.config(text="開始錄影", bg="red")
            self.status_label.config(text="錄影已停止", fg="blue")
        else:
            self.is_recording = True
            self.record_btn.config(text="停止錄影", bg="darkred")
            self.status_label.config(text="正在錄影...", fg="red")
    
    def stop_app(self):
        """停止應用程式"""
        self.is_server = False
        self.is_client = False
        
        if self.relay_socket:
            self.relay_socket.close()
        
        self.root.quit()
    
    def run(self):
        self.root.mainloop()

if __name__ == '__main__':
    app = CameraStreamFreeApp()
    app.run()
