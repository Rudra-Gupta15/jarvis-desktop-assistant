import os
import subprocess
import pyautogui
import psutil
import webbrowser
import platform

# Issue 6: Windows-only imports with graceful degradation
IS_WINDOWS = platform.system() == "Windows"

if IS_WINDOWS:
    import wmi
    import screen_brightness_control as sbc
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
else:
    # Mocks or alternative logic could go here for Linux/Mac
    pass
from datetime import datetime

class JarvisAutomation:
    def __init__(self):
        pyautogui.FAILSAFE = True

    def open_app(self, app_name):
        """Try to open an application by name with fuzzy search support."""
        print(f"JARVIS: Searching for application '{app_name}'...")
        try:
            # Issue 11: Expanded hardcoded quick-links & Aliases
            apps = {
                # Browsers
                "chrome": "chrome.exe",
                "google chrome": "chrome.exe",
                "edge": "msedge.exe",
                "microsoft edge": "msedge.exe",
                "brave": "brave.exe",
                "firefox": "firefox.exe",
                # System
                "notepad": "notepad.exe",
                "calc": "calc.exe",
                "calculator": "calc.exe",
                "explorer": "explorer.exe",
                "file explorer": "explorer.exe",
                "files": "explorer.exe",
                "fileexplorer": "explorer.exe",
                "windows explorer": "explorer.exe",
                "cmd": "cmd.exe",
                "terminal": "wt.exe",
                "powershell": "powershell.exe",
                "task manager": "taskmgr.exe",
                "control panel": "control",
                "settings": "ms-settings:",
                "store": "ms-windows-store:",
                "microsoft store": "ms-windows-store:",
                "microsoft_store": "ms-windows-store:",
                # Communication & Dev
                "whatsapp": "whatsapp:", 
                "discord": "discord:///guest-join/",
                "spotify": "spotify:",
                "steam": "steam://",
                "epic": "com.epicgames.launcher:",
                "unity": "unityhub://",
                "unity hub": "unityhub://",
                "unityhub": "unityhub://",
                "code": "code",
                "vscode": "code",
                "studio": "code",
                # Office
                "word": "winword.exe",
                "excel": "excel.exe",
                "powerpoint": "powerpnt.exe",
            }
            
            clean_name = app_name.lower().replace("_", " ").strip()
            
            # 1. Check exact/alias matches
            if clean_name in apps:
                os.startfile(apps[clean_name])
                return f"Launched {app_name}"

            # 2. Keyword/Fuzzy Match (e.g. "explorer" in "fileexplorer")
            for key, path in apps.items():
                if key in clean_name or clean_name in key:
                    print(f"JARVIS: Fuzzy matched '{app_name}' to '{key}'")
                    os.startfile(path)
                    return f"Matched and launched {key}"

            # 3. Try generic 'start' command (Windows Shell execution)
            # Wrap in quotes to handle spaces properly
            try:
                subprocess.Popen(f'start "" "{app_name}"', shell=True)
                return f"Executed system trigger for {app_name}"
            except:
                pass

            # 4. Search Start Menu for .lnk files
            # ... (rest of search logic)
            start_menu_paths = [
                os.path.join(os.environ["ProgramData"], "Microsoft", "Windows", "Start Menu", "Programs"),
                os.path.join(os.environ["AppData"], "Microsoft", "Windows", "Start Menu", "Programs")
            ]
            
            for path in start_menu_paths:
                if not os.path.exists(path): continue
                for root, dirs, files in os.walk(path):
                    for file in files:
                        if clean_name in file.lower() and file.endswith(".lnk"):
                            full_path = os.path.join(root, file)
                            os.startfile(full_path)
                            return f"Found and opened {file} via Start Menu"

            # 5. Web-Fallback for common services (Issue 15: Popular web apps)
            web_fallbacks = {
                "youtube": "https://youtube.com",
                "google": "https://google.com",
                "gmail": "https://mail.google.com",
                "netflix": "https://netflix.com",
                "spotify": "https://open.spotify.com",
                "github": "https://github.com",
                "reddit": "https://reddit.com",
                "twitter": "https://x.com",
                "meta": "https://facebook.com",
                "facebook": "https://facebook.com",
                "instagram": "https://instagram.com",
                "chatgpt": "https://chat.openai.com",
                "amazon": "https://amazon.com",
            }

            if clean_name in web_fallbacks:
                print(f"JARVIS: Local app '{app_name}' not found. Falling back to {web_fallbacks[clean_name]}")
                return self.open_url(web_fallbacks[clean_name])

            # 6. Final check: if it looks like a domain, try opening it as a URL
            if "." in app_name and " " not in app_name:
                 return self.open_url(f"https://{app_name}" if not app_name.startswith("http") else app_name)

            return f"I couldn't find a reliable way to launch '{app_name}' locally or as a web-service. You might need to add a custom shortcut."
        except Exception as e:
            return f"Error launching {app_name}: {e}"

    def check_dependencies(self):
        """Diagnostic check for core binary dependencies."""
        report = []
        
        # Check Tesseract
        try:
            import pytesseract
            # This triggers a check if the path is valid/executable
            pytesseract.get_tesseract_version()
            report.append("✅ Vision: Tesseract OCR is online.")
        except Exception:
            report.append("❌ Vision: Tesseract NOT FOUND. Screen reading disabled.")

        # Check WMI
        if IS_WINDOWS:
            try:
                import wmi
                wmi.WMI()
                report.append("✅ System: WMI Core is online.")
            except Exception:
                report.append("❌ System: WMI Error. Hardware specs unavailable.")
        else:
            report.append("ℹ️  System: Non-Windows platform. Hardware specs limited.")

        return "\n".join(report)

    def open_folder(self, folder_path):
        """Open a local folder on the system with dynamic path resolution."""
        print(f"JARVIS: Opening folder {folder_path}...")
        try:
            # Issue 15: Dynamic Path Resolution
            # Resolve placeholders like 'Username' or 'YourName' to actual home dir
            normalized_path = folder_path
            placeholders = ["Username", "User", "YourName", "<User>", "{Username}"]
            
            # Check if path starts with C:\Users\Placeholder
            for p in placeholders:
                if f"Users\\{p}" in folder_path:
                    home = os.path.expanduser("~")
                    normalized_path = folder_path.replace(f"Users\\{p}", f"Users\\{os.path.basename(home)}")
                    print(f"JARVIS: Resolved placeholder path to: {normalized_path}")
                    break
            
            # On Windows, os.startfile opens folders in Explorer
            if os.path.exists(normalized_path):
                os.startfile(normalized_path)
                return f"Opened folder {normalized_path}"
            else:
                return f"Folder not found: {normalized_path}"
        except Exception as e:
            return f"Failed to open folder: {e}"

    def open_url(self, url):
        """Open a URL in the default browser."""
        print(f"JARVIS: Opening URL {url}...")
        try:
            webbrowser.open(url)
            return f"Opened {url}"
        except Exception as e:
            return f"Failed to open URL: {e}"

    def get_system_stats(self):
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        return f"CPU Usage: {cpu}%, RAM Usage: {ram}%"

    def get_detailed_specs(self):
        """Fetch actual hardware specifications."""
        print("JARVIS: Fetching system hardware details...")
        if not IS_WINDOWS:
            return f"OS: {platform.system()} {platform.release()} (Deep hardware specs unavailable on this platform)"

        try:
            w = wmi.WMI()
            # Computer System Info
            comp = w.Win32_ComputerSystem()[0]
            mfg = comp.Manufacturer
            model = comp.Model
            
            # CPU Info
            processor = w.Win32_Processor()[0].Name
            
            # RAM Info
            total_ram = round(int(comp.TotalPhysicalMemory) / (1024**3), 1)
            
            # GPU Info
            gpus = [gpu.Name for gpu in w.Win32_VideoController()]
            gpu_info = ", ".join(gpus)
            
            specs = (
                f"Manufacturer: {mfg}\n"
                f"Model: {model}\n"
                f"CPU: {processor}\n"
                f"RAM: {total_ram} GB\n"
                f"GPU: {gpu_info}\n"
                f"OS: {platform.system()} {platform.release()}"
            )
            return specs
        except Exception as e:
            return f"Error retrieving specs: {e}"

    def set_brightness(self, level):
        """Set screen brightness (0-100)."""
        if not IS_WINDOWS:
            return "Brightness control only supported on Windows."
        try:
            level = max(0, min(100, int(level)))
            sbc.set_brightness(level)
            return f"Brightness set to {level}%"
        except Exception as e:
            return f"Failed to set brightness: {e}"

    def set_volume(self, level):
        """Set system volume (0-100)."""
        if not IS_WINDOWS:
            return "Volume control only supported on Windows via pycaw."
        try:
            level = max(0, min(100, int(level)))
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            volume.SetMasterVolumeLevelScalar(level / 100, None)
            return f"Volume set to {level}%"
        except Exception as e:
            return f"Failed to set volume: {e}"

    def toggle_mute(self):
        """Toggle system mute."""
        if not IS_WINDOWS:
            return "Mute toggle only supported on Windows via pycaw."
        try:
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            mute = volume.GetMute()
            volume.SetMute(not mute, None)
            return "System muted" if not mute else "System unmuted"
        except Exception as e:
            return f"Failed to toggle mute: {e}"

    def take_screenshot(self):
        """Capture screenshot and save to a file."""
        import mss
        try:
            os.makedirs("screenshots", exist_ok=True)
            filename = f"screenshots/screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            with mss.mss() as sct:
                sct.shot(output=filename)
            return f"Screenshot saved as {filename}"
        except Exception as e:
            return f"Failed to take screenshot: {e}"

    def press_key(self, key):
        pyautogui.press(key)

    def type_text(self, text):
        pyautogui.write(text)

if __name__ == "__main__":
    auto = JarvisAutomation()
    print("--- SYSTEM STATS ---")
    print(auto.get_system_stats())
    print("\n--- DETAILED SPECS ---")
    print(auto.get_detailed_specs())
    # print(auto.set_brightness(50))
