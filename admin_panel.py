import asyncio
import websockets
import json
import time
import socket
import threading
import hashlib
import secrets
import psutil
import platform
import subprocess
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
from datetime import datetime
from collections import defaultdict
import urllib.parse
import base64

# =====================================================
# CONFIGURATION
# =====================================================
ADMIN_USERNAME = "your_username"  # Change this
ADMIN_PASSWORD = "your_password"  # Change this
SESSION_TIMEOUT = 3600

# File Paths
LOGIN_FILE = "login.html"
DASHBOARD_FILE = "template1/dashboard.html"

# Port Settings
WS_PORT = 5555   # WebSocket port
HTTP_PORT = 9980 # Web interface port

# =====================================================
# SYSTEM CONTROLLER
# =====================================================
class SystemController:
    @staticmethod
    def shutdown():
        try:
            if platform.system() == "Windows":
                os.system("shutdown /s /t 1")
            else:
                os.system("shutdown -h now")
            return {"success": True, "message": "Shutting down..."}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def restart():
        try:
            if platform.system() == "Windows":
                os.system("shutdown /r /t 1")
            else:
                os.system("shutdown -r now")
            return {"success": True, "message": "Restarting..."}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def sleep():
        try:
            if platform.system() == "Windows":
                os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            else:
                os.system("systemctl suspend")
            return {"success": True, "message": "Going to sleep..."}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def lock():
        try:
            if platform.system() == "Windows":
                os.system("rundll32.exe user32.dll,LockWorkStation")
            else:
                os.system("gnome-screensaver-command -l")
            return {"success": True, "message": "Screen locked"}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def _get_audio_interface(device_type='speaker'):
        try:
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            
            enumerator = AudioUtilities.GetDeviceEnumerator()
            from pycaw.constants import EDataFlow, ERole
            
            if device_type == 'speaker':
                endpoint = enumerator.GetDefaultAudioEndpoint(
                    EDataFlow.eRender.value, 
                    ERole.eMultimedia.value
                )
            else:
                endpoint = enumerator.GetDefaultAudioEndpoint(
                    EDataFlow.eCapture.value, 
                    ERole.eMultimedia.value
                )
            
            interface = endpoint.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            
            return volume
        except Exception as e:
            raise Exception(f"Audio interface error: {str(e)}")
    
    @staticmethod
    def set_volume(level):
        try:
            if platform.system() == "Windows":
                volume = SystemController._get_audio_interface('speaker')
                volume.SetMasterVolumeLevelScalar(level / 100, None)
            else:
                os.system(f"amixer -D pulse sset Master {level}%")
            return {"success": True, "message": f"Volume set to {level}%"}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def mute_audio(mute=True):
        try:
            if platform.system() == "Windows":
                volume = SystemController._get_audio_interface('speaker')
                volume.SetMute(1 if mute else 0, None)
            else:
                os.system("amixer -D pulse sset Master mute" if mute else "amixer -D pulse sset Master unmute")
            return {"success": True, "message": "Audio muted" if mute else "Audio unmuted"}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def set_mic_volume(level):
        try:
            if platform.system() == "Windows":
                volume = SystemController._get_audio_interface('microphone')
                volume.SetMasterVolumeLevelScalar(level / 100, None)
                return {"success": True, "message": f"Microphone set to {level}%"}
            else:
                os.system(f"amixer -D pulse sset Capture {level}%")
                return {"success": True, "message": f"Microphone set to {level}%"}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def mute_mic(mute=True):
        try:
            if platform.system() == "Windows":
                volume = SystemController._get_audio_interface('microphone')
                volume.SetMute(1 if mute else 0, None)
                return {"success": True, "message": "Mic muted" if mute else "Mic unmuted"}
            else:
                os.system("amixer -D pulse sset Capture mute" if mute else "amixer -D pulse sset Capture unmute")
                return {"success": True, "message": "Mic muted" if mute else "Mic unmuted"}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def get_audio_status():
        try:
            if platform.system() == "Windows":
                try:
                    speaker_volume_obj = SystemController._get_audio_interface('speaker')
                    speaker_volume = int(speaker_volume_obj.GetMasterVolumeLevelScalar() * 100)
                    speaker_muted = bool(speaker_volume_obj.GetMute())
                except Exception as e:
                    speaker_volume = 50
                    speaker_muted = False
                
                try:
                    mic_volume_obj = SystemController._get_audio_interface('microphone')
                    mic_volume = int(mic_volume_obj.GetMasterVolumeLevelScalar() * 100)
                    mic_muted = bool(mic_volume_obj.GetMute())
                except Exception as e:
                    mic_volume = 50
                    mic_muted = False
                
                return {
                    "success": True,
                    "speaker_volume": speaker_volume,
                    "speaker_muted": speaker_muted,
                    "mic_volume": mic_volume,
                    "mic_muted": mic_muted
                }
            else:
                return {
                    "success": True, 
                    "speaker_volume": 50, 
                    "speaker_muted": False, 
                    "mic_volume": 50, 
                    "mic_muted": False
                }
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def run_command(command):
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
            return {
                "success": True,
                "output": result.stdout,
                "error": result.stderr,
                "returncode": result.returncode
            }
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def open_application(app_name, foreground=True):
        try:
            if platform.system() == "Windows":
                if foreground:
                    subprocess.Popen(app_name, shell=True)
                else:
                    subprocess.Popen(app_name, shell=True, 
                                   creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS)
            else:
                os.system(f"open {app_name}" if platform.system() == "Darwin" else f"{app_name} &")
            return {"success": True, "message": f"Opening {app_name}"}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def show_message(title, message):
        try:
            if platform.system() == "Windows":
                import ctypes
                MB_OK = 0x0
                MB_ICONINFORMATION = 0x40
                MB_TOPMOST = 0x40000
                MB_SETFOREGROUND = 0x10000
                
                ctypes.windll.user32.MessageBoxW(
                    0, 
                    message, 
                    title, 
                    MB_OK | MB_ICONINFORMATION | MB_TOPMOST | MB_SETFOREGROUND
                )
            else:
                os.system(f'notify-send "{title}" "{message}"')
            return {"success": True, "message": "Message shown"}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def get_screenshot():
        try:
            from PIL import ImageGrab
            import io
            
            screenshot = ImageGrab.grab()
            buffer = io.BytesIO()
            screenshot.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()
            
            return {"success": True, "image": img_str}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def kill_process(pid):
        try:
            process = psutil.Process(pid)
            process.terminate()
            return {"success": True, "message": f"Process {pid} terminated"}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def monitor_off():
        try:
            if platform.system() == "Windows":
                import ctypes
                ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, 2)
            else:
                os.system("xset dpms force off")
            return {"success": True, "message": "Monitor turned off"}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def monitor_on():
        try:
            if platform.system() == "Windows":
                import ctypes
                ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, -1)
            else:
                os.system("xset dpms force on")
            return {"success": True, "message": "Monitor turned on"}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def get_drives():
        try:
            drives = []
            if platform.system() == "Windows":
                import string
                from ctypes import windll
                
                bitmask = windll.kernel32.GetLogicalDrives()
                for letter in string.ascii_uppercase:
                    if bitmask & 1:
                        drive_path = f"{letter}:\\"
                        try:
                            usage = psutil.disk_usage(drive_path)
                            drives.append({
                                'name': letter,
                                'path': drive_path,
                                'total': usage.total,
                                'used': usage.used,
                                'free': usage.free,
                                'percent': usage.percent
                            })
                        except:
                            pass
                    bitmask >>= 1
            else:
                partitions = psutil.disk_partitions()
                for partition in partitions:
                    try:
                        usage = psutil.disk_usage(partition.mountpoint)
                        drives.append({
                            'name': partition.device.split('/')[-1],
                            'path': partition.mountpoint,
                            'total': usage.total,
                            'used': usage.used,
                            'free': usage.free,
                            'percent': usage.percent
                        })
                    except:
                        pass
            
            return {"success": True, "drives": drives}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def list_directory(path):
        try:
            path = os.path.normpath(path)
            
            if len(path) == 2 and path[1] == ':':
                path = path + '\\'
            
            items = []
            for item in os.listdir(path):
                full_path = os.path.join(path, item)
                is_dir = os.path.isdir(full_path)
                try:
                    size = os.path.getsize(full_path) if not is_dir else 0
                    modified = os.path.getmtime(full_path)
                except:
                    size = 0
                    modified = 0
                
                items.append({
                    'name': item,
                    'path': full_path,
                    'is_dir': is_dir,
                    'size': size,
                    'modified': modified
                })
            
            items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
            
            return {"success": True, "items": items, "current_path": path}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def delete_file(path):
        try:
            if os.path.isdir(path):
                import shutil
                shutil.rmtree(path)
            else:
                os.remove(path)
            return {"success": True, "message": f"Deleted {path}"}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def create_folder(path):
        try:
            os.makedirs(path, exist_ok=True)
            return {"success": True, "message": f"Created {path}"}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def rename_item(old_path, new_name):
        try:
            directory = os.path.dirname(old_path)
            new_path = os.path.join(directory, new_name)
            os.rename(old_path, new_path)
            return {"success": True, "message": f"Renamed to {new_name}"}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def read_file(path, binary=False):
        try:
            if binary:
                with open(path, 'rb') as f:
                    content = base64.b64encode(f.read()).decode('utf-8')
                return {"success": True, "content": content, "binary": True}
            else:
                encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
                for encoding in encodings:
                    try:
                        with open(path, 'r', encoding=encoding) as f:
                            content = f.read()
                        return {"success": True, "content": content, "binary": False, "encoding": encoding}
                    except UnicodeDecodeError:
                        continue
                with open(path, 'rb') as f:
                    content = f.read().decode('utf-8', errors='replace')
                return {"success": True, "content": content, "binary": False, "encoding": "binary"}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def write_file(path, content, binary=False):
        try:
            if binary:
                content_bytes = base64.b64decode(content)
                with open(path, 'wb') as f:
                    f.write(content_bytes)
            else:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
            return {"success": True, "message": f"File saved: {path}"}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def create_file(path):
        try:
            with open(path, 'w') as f:
                f.write('')
            return {"success": True, "message": f"File created: {path}"}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def download_file(path):
        try:
            with open(path, 'rb') as f:
                content = base64.b64encode(f.read()).decode('utf-8')
            filename = os.path.basename(path)
            return {"success": True, "content": content, "filename": filename}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def upload_file(path, content_base64, filename):
        try:
            content = base64.b64decode(content_base64)
            full_path = os.path.join(path, filename)
            with open(full_path, 'wb') as f:
                f.write(content)
            return {"success": True, "message": f"File uploaded: {filename}"}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def get_exe_icon(exe_path):
        try:
            if not os.path.exists(exe_path) or not exe_path.endswith('.exe'):
                return None
                
            import win32gui
            import win32ui
            import win32con
            import win32api
            from PIL import Image
            import io
            
            ico_x = win32api.GetSystemMetrics(win32con.SM_CXICON)
            ico_y = win32api.GetSystemMetrics(win32con.SM_CYICON)
            
            large, small = win32gui.ExtractIconEx(exe_path, 0)
            
            if not large:
                return None
            
            hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
            hbmp = win32ui.CreateBitmap()
            hbmp.CreateCompatibleBitmap(hdc, ico_x, ico_y)
            hdc = hdc.CreateCompatibleDC()
            
            hdc.SelectObject(hbmp)
            hdc.DrawIcon((0, 0), large[0])
            
            bmpinfo = hbmp.GetInfo()
            bmpstr = hbmp.GetBitmapBits(True)
            
            img = Image.frombuffer(
                'RGBA',
                (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                bmpstr, 'raw', 'BGRA', 0, 1
            )
            
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            win32gui.DestroyIcon(large[0])
            if small:
                win32gui.DestroyIcon(small[0])
            
            return img_base64
            
        except Exception as e:
            return None
    
    @staticmethod
    def categorize_app_by_path(app_name, app_path):
        name_lower = app_name.lower()
        path_lower = app_path.lower()
        
        if 'nvidia corporation' in path_lower or 'nvidia' in path_lower:
            return 'nvidia'
        
        if 'windows defender' in path_lower or 'defender' in path_lower:
            return 'security'
        
        if 'steam' in path_lower and ('program files' in path_lower or 'steamapps' in path_lower):
            return 'games'
        
        if 'internet explorer' in path_lower or 'hyper-v' in path_lower:
            return 'system'
        
        if 'program files' in path_lower and 'windows' in path_lower.split('\\')[-2:]:
            return 'system'
        
        browsers = ['chrome', 'firefox', 'edge', 'opera', 'brave', 'safari']
        office = ['word', 'excel', 'powerpoint', 'outlook', 'notepad', 'libreoffice', 'openoffice']
        media = ['vlc', 'spotify', 'itunes', 'media player', 'paint', 'photoshop', 'gimp']
        dev = ['visual studio', 'vscode', 'pycharm', 'git', 'python', 'node', 'java']
        system = ['cmd', 'powershell', 'taskmgr', 'regedit', 'explorer', 'control', 'msconfig']
        security = ['antivirus', 'firewall', 'malware', 'kaspersky', 'avast', 'norton', 'mcafee']
        games = ['steam', 'epic', 'origin', 'uplay', 'battle.net', 'minecraft', 'roblox']
        nvidia_apps = ['geforce', 'nvidia', 'physx', 'cuda']
        
        for keyword in browsers:
            if keyword in name_lower:
                return 'browsers'
        
        for keyword in office:
            if keyword in name_lower:
                return 'office'
        
        for keyword in media:
            if keyword in name_lower:
                return 'media'
        
        for keyword in dev:
            if keyword in name_lower:
                return 'dev'
        
        for keyword in nvidia_apps:
            if keyword in name_lower:
                return 'nvidia'
        
        for keyword in security:
            if keyword in name_lower:
                return 'security'
        
        for keyword in games:
            if keyword in name_lower:
                return 'games'
        
        for keyword in system:
            if keyword in name_lower:
                return 'system'
        
        return 'other'
    
    @staticmethod
    def scan_applications():
        try:
            applications = []
            
            if platform.system() == "Windows":
                import winreg
                
                search_paths = [
                    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
                    (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
                    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
                ]
                
                seen_apps = set()
                
                for hkey, reg_path in search_paths:
                    try:
                        key = winreg.OpenKey(hkey, reg_path)
                        for i in range(winreg.QueryInfoKey(key)[0]):
                            try:
                                subkey_name = winreg.EnumKey(key, i)
                                subkey = winreg.OpenKey(key, subkey_name)
                                
                                try:
                                    name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                                    path = ""
                                    icon_path = ""
                                    
                                    try:
                                        icon_path = winreg.QueryValueEx(subkey, "DisplayIcon")[0]
                                        if "," in icon_path:
                                            icon_path = icon_path.split(",")[0]
                                        icon_path = icon_path.strip('"').strip()
                                        path = icon_path
                                    except:
                                        pass
                                    
                                    if not path:
                                        try:
                                            install_loc = winreg.QueryValueEx(subkey, "InstallLocation")[0]
                                            if install_loc and os.path.exists(install_loc):
                                                for file in os.listdir(install_loc):
                                                    if file.endswith('.exe'):
                                                        path = os.path.join(install_loc, file)
                                                        icon_path = path
                                                        break
                                        except:
                                            pass
                                    
                                    app_key = name.lower()
                                    if app_key in seen_apps:
                                        continue
                                    seen_apps.add(app_key)
                                    
                                    skip_keywords = ['update', 'redistributable', 'runtime', 'driver', 
                                                   'hotfix', 'security update', 'kb', 'service pack']
                                    if any(keyword in name.lower() for keyword in skip_keywords):
                                        continue
                                    
                                    if name and len(name) > 2:
                                        icon_base64 = None
                                        if icon_path and os.path.exists(icon_path) and icon_path.endswith('.exe'):
                                            icon_base64 = SystemController.get_exe_icon(icon_path)
                                        
                                        category = SystemController.categorize_app_by_path(name, path if path else "")
                                        
                                        applications.append({
                                            'name': name,
                                            'path': path if path else name,
                                            'icon': icon_base64,
                                            'category': category
                                        })
                                except:
                                    pass
                                
                                winreg.CloseKey(subkey)
                            except:
                                pass
                        winreg.CloseKey(key)
                    except:
                        pass
                
                common_apps = [
                    {'name': 'Notepad', 'path': 'C:\\Windows\\System32\\notepad.exe', 'category': 'office'},
                    {'name': 'Calculator', 'path': 'C:\\Windows\\System32\\calc.exe', 'category': 'system'},
                    {'name': 'Paint', 'path': 'C:\\Windows\\System32\\mspaint.exe', 'category': 'media'},
                    {'name': 'Command Prompt', 'path': 'C:\\Windows\\System32\\cmd.exe', 'category': 'system'},
                    {'name': 'PowerShell', 'path': 'C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe', 'category': 'system'},
                    {'name': 'Task Manager', 'path': 'C:\\Windows\\System32\\taskmgr.exe', 'category': 'system'},
                    {'name': 'Windows Explorer', 'path': 'C:\\Windows\\explorer.exe', 'category': 'system'},
                    {'name': 'Registry Editor', 'path': 'C:\\Windows\\regedit.exe', 'category': 'system'},
                    {'name': 'Control Panel', 'path': 'C:\\Windows\\System32\\control.exe', 'category': 'system'},
                ]
                
                for app in common_apps:
                    if os.path.exists(app['path']):
                        app_key = app['name'].lower()
                        if app_key not in seen_apps:
                            seen_apps.add(app_key)
                            icon_base64 = SystemController.get_exe_icon(app['path'])
                            app['icon'] = icon_base64
                            applications.append(app)
                
                applications.sort(key=lambda x: x['name'].lower())
                
                return {"success": True, "applications": applications}
                
            else:
                common_apps = [
                    {'name': 'Terminal', 'path': 'gnome-terminal', 'icon': None, 'category': 'system'},
                    {'name': 'Firefox', 'path': 'firefox', 'icon': None, 'category': 'browsers'},
                    {'name': 'Chrome', 'path': 'google-chrome', 'icon': None, 'category': 'browsers'},
                    {'name': 'Files', 'path': 'nautilus', 'icon': None, 'category': 'system'},
                ]
                return {"success": True, "applications": common_apps}
                
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def open_special_file(path):
        try:
            ext = os.path.splitext(path)[1].lower()
            
            if platform.system() == "Windows":
                if ext == '.lnk':
                    os.startfile(path)
                    return {"success": True, "message": f"Opening shortcut: {path}"}
                
                elif ext == '.url':
                    os.startfile(path)
                    return {"success": True, "message": f"Opening URL: {path}"}
                
                elif ext == '.msi':
                    subprocess.Popen(['msiexec', '/i', path], shell=True)
                    return {"success": True, "message": f"Running installer: {path}"}
                
                else:
                    os.startfile(path)
                    return {"success": True, "message": f"Opening: {path}"}
            else:
                if platform.system() == "Darwin":
                    subprocess.Popen(['open', path])
                else:
                    subprocess.Popen(['xdg-open', path])
                return {"success": True, "message": f"Opening: {path}"}
                
        except Exception as e:
            return {"success": False, "message": str(e)}

# =====================================================
# SESSION YÖNETİMİ
# =====================================================
class SessionManager:
    def __init__(self):
        self.sessions = {}
        self.active_clients = {}
        self.stats = {
            'total_requests': 0,
            'total_pings': 0,
            'active_connections': 0,
            'uptime_start': time.time(),
            'ping_history': [],
            'client_history': []
        }
        
    def create_session(self, username):
        token = secrets.token_urlsafe(32)
        self.sessions[token] = {
            'username': username,
            'created': time.time(),
            'last_activity': time.time()
        }
        return token
    
    def validate_session(self, token):
        if token in self.sessions:
            session = self.sessions[token]
            if time.time() - session['last_activity'] < SESSION_TIMEOUT:
                session['last_activity'] = time.time()
                return True
        return False
    
    def delete_session(self, token):
        if token in self.sessions:
            del self.sessions[token]

session_manager = SessionManager()

# =====================================================
# ADMIN SERVER
# =====================================================
class AdminServer:
    def __init__(self, ws_port=WS_PORT, http_port=HTTP_PORT):
        self.ws_port = ws_port
        self.http_port = http_port
        self.local_ip = self.get_local_ip()
        self.clients = {}
        self.admin_clients = set()
        self.last_network = psutil.net_io_counters()
        self.last_network_time = time.time()
        self.peak_clients = 0
        
    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except:
            return "127.0.0.1"
    
    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_login(self, username, password):
        password_hash = self.hash_password(password)
        correct_hash = self.hash_password(ADMIN_PASSWORD)
        return username == ADMIN_USERNAME and password_hash == correct_hash
    
    def get_disk_info(self):
        disks = []
        try:
            partitions = psutil.disk_partitions()
            for partition in partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disks.append({
                        'device': partition.device,
                        'mountpoint': partition.mountpoint,
                        'total_gb': round(usage.total / (1024**3), 2),
                        'used_gb': round(usage.used / (1024**3), 2),
                        'free_gb': round(usage.free / (1024**3), 2),
                        'percent': usage.percent
                    })
                except:
                    pass
        except:
            pass
        return disks
    
    def get_system_stats(self):
        current_network = psutil.net_io_counters()
        current_time = time.time()
        time_delta = current_time - self.last_network_time
        
        if time_delta > 0:
            sent_speed = (current_network.bytes_sent - self.last_network.bytes_sent) / time_delta
            recv_speed = (current_network.bytes_recv - self.last_network.bytes_recv) / time_delta
        else:
            sent_speed = 0
            recv_speed = 0
        
        self.last_network = current_network
        self.last_network_time = current_time

        processes = []
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    info = proc.info
                    processes.append({
                        'pid': info['pid'],
                        'name': info['name'],
                        'cpu': round(info['cpu_percent'] or 0, 1),
                        'mem': round(info['memory_percent'] or 0, 1)
                    })
                except:
                    pass
            processes.sort(key=lambda x: x['cpu'], reverse=True)
        except:
            pass

        current_client_count = len(self.clients)
        if current_client_count > self.peak_clients:
            self.peak_clients = current_client_count

        ping_history = []
        for client_info in self.clients.values():
            if client_info.get('last_ping', 0) > 0:
                ping_history.append(client_info['last_ping'])
        
        if ping_history:
            session_manager.stats['ping_history'] = (session_manager.stats.get('ping_history', []) + ping_history)[-100:]
        
        return {
            'cpu': psutil.cpu_percent(interval=0.1),
            'ram': psutil.virtual_memory().percent,
            'network': {
                'sent': sent_speed,
                'recv': recv_speed
            },
            'network_total': {
                'sent': current_network.bytes_sent,
                'recv': current_network.bytes_recv
            },
            'uptime': time.time() - session_manager.stats['uptime_start'],
            'active_clients': len(self.clients),
            'clients': [
                {
                    'ip': client_id,
                    'connected': info['connected'],
                    'ping': info.get('last_ping', 0),
                    'packets': info.get('packets', 0),
                    'status': 'online' if time.time() - info.get('last_activity', 0) < 10 else 'offline'
                }
                for client_id, info in self.clients.items()
            ],
            'system_info': {
                'os': platform.system(),
                'platform': platform.platform(),
                'arch': platform.machine(),
                'cores': psutil.cpu_count(),
                'ram': f"{psutil.virtual_memory().total / (1024**3):.1f} GB",
                'boot_time': datetime.fromtimestamp(psutil.boot_time()).strftime('%Y-%m-%d %H:%M:%S')
            },
            'processes': processes[:20],
            'disks': self.get_disk_info(),
            'stats': {
                'total_requests': session_manager.stats['total_requests'],
                'total_pings': session_manager.stats['total_pings'],
                'ping_history': session_manager.stats.get('ping_history', []),
                'peak_clients': self.peak_clients
            }
        }
    
    def handle_control_command(self, action, data):
        print(f"🎮 Control: {action}")
        
        if action == 'shutdown':
            return SystemController.shutdown()
        elif action == 'restart':
            return SystemController.restart()
        elif action == 'sleep':
            return SystemController.sleep()
        elif action == 'lock':
            return SystemController.lock()
        elif action == 'volume':
            return SystemController.set_volume(int(data.get('level', 50)))
        elif action == 'mute':
            return SystemController.mute_audio(data.get('mute', True))
        elif action == 'mic_volume':
            return SystemController.set_mic_volume(int(data.get('level', 50)))
        elif action == 'mic_mute':
            return SystemController.mute_mic(data.get('mute', True))
        elif action == 'get_audio_status':
            return SystemController.get_audio_status()
        elif action == 'monitor_off':
            return SystemController.monitor_off()
        elif action == 'monitor_on':
            return SystemController.monitor_on()
        elif action == 'open_app':
            foreground = data.get('foreground', True)
            return SystemController.open_application(data.get('app', ''), foreground)
        elif action == 'message':
            return SystemController.show_message(data.get('title', 'Message'), data.get('message', ''))
        elif action == 'screenshot':
            return SystemController.get_screenshot()
        elif action == 'command':
            result = SystemController.run_command(data.get('command', ''))
            result['command'] = data.get('command', '')
            return result
        elif action == 'kill_process':
            return SystemController.kill_process(int(data.get('pid', 0)))
        elif action == 'get_drives':
            return SystemController.get_drives()
        elif action == 'list_directory':
            return SystemController.list_directory(data.get('path', 'C:\\'))
        elif action == 'delete_file':
            return SystemController.delete_file(data.get('path', ''))
        elif action == 'create_folder':
            return SystemController.create_folder(data.get('path', ''))
        elif action == 'rename_item':
            return SystemController.rename_item(data.get('old_path', ''), data.get('new_name', ''))
        elif action == 'read_file':
            binary = data.get('binary', False)
            return SystemController.read_file(data.get('path', ''), binary)
        elif action == 'write_file':
            binary = data.get('binary', False)
            return SystemController.write_file(data.get('path', ''), data.get('content', ''), binary)
        elif action == 'create_file':
            return SystemController.create_file(data.get('path', ''))
        elif action == 'download_file':
            return SystemController.download_file(data.get('path', ''))
        elif action == 'upload_file':
            return SystemController.upload_file(data.get('path', ''), data.get('content', ''), data.get('filename', ''))
        elif action == 'scan_applications':
            return SystemController.scan_applications()
        elif action == 'open_special_file':
            return SystemController.open_special_file(data.get('path', ''))
        else:
            return {"success": False, "message": "Unknown command"}
    
    class HTTPHandler(SimpleHTTPRequestHandler):
        admin_server = None
        
        def do_GET(self):
            # Ana sayfa / Login
            if self.path == '/' or self.path == '/login':
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                try:
                    with open(LOGIN_FILE, 'r', encoding='utf-8') as f:
                        self.wfile.write(f.read().encode('utf-8'))
                except FileNotFoundError:
                    self.wfile.write(f'<h1>Error: {LOGIN_FILE} not found</h1>'.encode('utf-8'))
            
            # Dashboard - Direkt Template1'e yönlendir
            elif self.path.startswith('/dashboard'):
                query = urllib.parse.urlparse(self.path).query
                params = urllib.parse.parse_qs(query)
                token = params.get('token', [None])[0]
                
                if not token or not session_manager.validate_session(token):
                    self.send_response(302)
                    self.send_header('Location', '/')
                    self.end_headers()
                    return
                
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                try:
                    with open(DASHBOARD_FILE, 'r', encoding='utf-8') as f:
                        self.wfile.write(f.read().encode('utf-8'))
                except FileNotFoundError:
                    self.wfile.write(f'<h1>Error: {DASHBOARD_FILE} not found</h1>'.encode('utf-8'))
            else:
                self.send_error(404)
        
        def do_POST(self):
            if self.path == '/api/login':
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                
                try:
                    data = json.loads(post_data.decode('utf-8'))
                    username = data.get('username')
                    password = data.get('password')
                    
                    if self.admin_server.verify_login(username, password):
                        token = session_manager.create_session(username)
                        response = {'success': True, 'token': token}
                        print(f"✅ Login: {username}")
                    else:
                        response = {'success': False, 'message': 'Invalid credentials'}
                        print(f"❌ Failed: {username}")
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(response).encode('utf-8'))
                except Exception as e:
                    print(f"❌ Error: {e}")
                    self.send_error(400)
            
            # Token validation endpoint
            elif self.path == '/api/validate-token':
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                
                try:
                    data = json.loads(post_data.decode('utf-8'))
                    token = data.get('token')
                    
                    valid = session_manager.validate_session(token)
                    
                    response = {'valid': valid}
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(response).encode('utf-8'))
                except Exception as e:
                    print(f"❌ Token validation error: {e}")
                    self.send_error(400)
            
            else:
                self.send_error(404)
        
        def log_message(self, format, *args):
            pass
    
    def start_http_server(self):
        AdminServer.HTTPHandler.admin_server = self
        httpd = HTTPServer(('0.0.0.0', self.http_port), AdminServer.HTTPHandler)
        print(f"🌐 HTTP: http://{self.local_ip}:{self.http_port}")
        httpd.serve_forever()
    
    async def handle_admin_websocket(self, websocket):
        client_ip = websocket.remote_address[0] if hasattr(websocket, 'remote_address') else "Unknown"
        path = websocket.request.path if hasattr(websocket, 'request') else websocket.path
        
        query = urllib.parse.urlparse(path).query
        params = urllib.parse.parse_qs(query)
        token = params.get('token', [None])[0]
        
        if not token or not session_manager.validate_session(token):
            await websocket.close(1008, "Unauthorized")
            return
        
        print(f"✅ Admin: {client_ip}")
        self.admin_clients.add(websocket)
        
        try:
            async def send_stats():
                while True:
                    try:
                        stats = self.get_system_stats()
                        await websocket.send(json.dumps(stats))
                        await asyncio.sleep(1)
                    except:
                        break
            
            async def receive_commands():
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        if data.get('type') == 'control':
                            response = self.handle_control_command(
                                data.get('action'),
                                data.get('data', {})
                            )
                            response['action'] = data.get('action')
                            await websocket.send(json.dumps({'control_response': response}))
                    except Exception as e:
                        print(f"❌ Control error: {e}")
            
            await asyncio.gather(send_stats(), receive_commands())
        except:
            pass
        finally:
            if websocket in self.admin_clients:
                self.admin_clients.remove(websocket)
            print(f"🔌 Admin left: {client_ip}")
    
    async def handle_client_websocket(self, websocket):
        client_ip = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        
        self.clients[client_ip] = {
            'connected': time.time(),
            'last_activity': time.time(),
            'packets': 0,
            'last_ping': 0
        }
        
        print(f"✅ Client: {client_ip}")
        
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    
                    if data.get('type') == 'ping':
                        self.clients[client_ip]['packets'] += 1
                        self.clients[client_ip]['last_activity'] = time.time()
                        session_manager.stats['total_pings'] += 1
                        
                        client_timestamp = data.get('timestamp', 0)
                        server_time = time.time() * 1000
                        ping = int(server_time - client_timestamp) if client_timestamp else 0
                        self.clients[client_ip]['last_ping'] = ping
                        
                        response = {
                            'type': 'pong',
                            'timestamp': data.get('timestamp'),
                            'server_time': server_time
                        }
                        await websocket.send(json.dumps(response))
                except:
                    pass
        except:
            pass
        finally:
            if client_ip in self.clients:
                del self.clients[client_ip]
            print(f"🔌 Client left: {client_ip}")
    
    async def websocket_handler(self, websocket):
        path = websocket.request.path if hasattr(websocket, 'request') else (websocket.path if hasattr(websocket, 'path') else '/')
        
        if '/admin' in path:
            await self.handle_admin_websocket(websocket)
        else:
            await self.handle_client_websocket(websocket)
    
    async def start_websocket_server(self):
        print(f"🔌 WebSocket: ws://{self.local_ip}:{self.ws_port}")
        async with websockets.serve(self.websocket_handler, '0.0.0.0', self.ws_port):
            await asyncio.Future()
    
    def run(self):
        print("=" * 60)
        print("🔐 ADMIN PANEL - REMOTE CONTROL SERVER")
        print("=" * 60)
        print(f"🌐 URL: http://{self.local_ip}:{self.http_port}")
        print(f"👤 User: {ADMIN_USERNAME}")
        print(f"🔑 Pass: {ADMIN_PASSWORD}")
        print("=" * 60)
        print("📁 File Structure:")
        print("   ├── login.html (main)")
        print("   └── template1/dashboard.html")
        print("=" * 60)
        
        if not os.path.exists(LOGIN_FILE):
            print(f"\n❌ ERROR: '{LOGIN_FILE}' not found in root!")
            return
        
        if not os.path.exists('template1'):
            print(f"\n❌ ERROR: 'template1' folder not found!")
            return
        
        if not os.path.exists(DASHBOARD_FILE):
            print(f"\n❌ ERROR: '{DASHBOARD_FILE}' not found!")
            return
        
        http_thread = threading.Thread(target=self.start_http_server, daemon=True)
        http_thread.start()
        
        try:
            asyncio.run(self.start_websocket_server())
        except KeyboardInterrupt:
            print("\n👋 Shutdown...")

if __name__ == "__main__":
    required_packages = {
        'websockets': 'websockets',
        'psutil': 'psutil',
        'PIL': 'pillow',
    }
    
    if platform.system() == "Windows":
        required_packages['pycaw'] = 'pycaw'
        required_packages['comtypes'] = 'comtypes'
        required_packages['win32gui'] = 'pywin32'
    
    missing_packages = []
    
    for package, pip_name in required_packages.items():
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(pip_name)
    
    if missing_packages:
        print("=" * 70)
        print("❌ MISSING PACKAGES")
        print("=" * 70)
        for package in missing_packages:
            print(f"   • {package}")
        print("\n📦 Install command:")
        print(f"   pip install {' '.join(missing_packages)}")
        print("=" * 70)
        exit(1)
    
    server = AdminServer()
    server.run()