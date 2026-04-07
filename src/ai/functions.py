import os
import sys
import subprocess
import datetime
import logging
import psutil
import json

logger = logging.getLogger(__name__)

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

# ========== APP NAME RESOLUTION ==========
APP_ALIASES = {
    "chrome": "Google Chrome",
    "code": "Visual Studio Code",
    "terminal": "Terminal",
    # ... (other aliases)
}

def resolve_app_name(app_name: str) -> str:
    key = app_name.lower().strip()
    return APP_ALIASES.get(key, app_name.title())

# ========== ACTION FUNCTIONS ==========
def open_application(app_name: str) -> str:
    try:
        app_name = resolve_app_name(app_name)
        if sys.platform == 'darwin':
            subprocess.run(['open', '-a', app_name], check=True)
        else:
            subprocess.run(['xdg-open', app_name], check=True)
        return f"{app_name} खोला जा रहा है।"
    except Exception as e:
        return f"सॉरी, {app_name} नहीं खुल रहा।"

def get_system_info() -> str:
    try:
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        return f"CPU: {cpu}% | RAM: {ram.percent}% | Disk: {disk.percent}% used."
    except Exception as e:
        return f"System info error: {e}"

def empty_trash() -> str:
    try:
        if sys.platform == 'darwin':
            subprocess.run(['osascript', '-e', 'tell application "Finder" to empty trash'], check=True)
            return "कचरा खाली कर दिया गया।"
        return "Not supported."
    except Exception as e:
        return f"Error: {e}"

def clean_downloads() -> str:
    try:
        download_path = os.path.expanduser('~/Downloads')
        for filename in os.listdir(download_path):
            file_path = os.path.join(download_path, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
        return "Downloads folder cleared."
    except Exception as e:
        return f"Error: {e}"

def set_brightness(level: int) -> str:
    try:
        if sys.platform == 'darwin':
            script = f'tell application "System Events" to set brightness of display 1 to {level/100}'
            subprocess.run(['osascript', '-e', script], check=True)
            return f"Brightness set to {level}%"
        return "Not supported."
    except Exception as e:
        return f"Brightness error: {e}"

def toggle_wifi() -> str:
    try:
        if sys.platform == 'darwin':
            status = subprocess.run(['networksetup', '-getairportpower', 'en0'], capture_output=True, text=True)
            state = 'off' if 'On' in status.stdout else 'on'
            subprocess.run(['networksetup', '-setairportpower', 'en0', state])
            return f"Wi-Fi turned {state}."
        return "Not supported."
    except Exception as e:
        return f"Wi-Fi error: {e}"

# ========== FUNCTION DEFINITIONS FOR LLM ==========
FUNCTIONS = [
    {
        "name": "open_application",
        "description": "Open an application.",
        "parameters": {"type": "object", "properties": {"app_name": {"type": "string"}}, "required": ["app_name"]}
    },
    {
        "name": "get_system_info",
        "description": "Get CPU, RAM, and Disk stats.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "empty_trash",
        "description": "Empty the trash bin.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "clean_downloads",
        "description": "Delete files in Downloads.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "set_brightness",
        "description": "Set brightness (0-100).",
        "parameters": {"type": "object", "properties": {"level": {"type": "integer"}}, "required": ["level"]}
    },
    {
        "name": "toggle_wifi",
        "description": "Toggle Wi-Fi on/off.",
        "parameters": {"type": "object", "properties": {}}
    }
]

def execute_function_call_by_name(name: str, args: dict):
    logger.info(f"Executing: {name} with {args}")
    global_func = globals().get(name)
    if global_func:
        try:
            return global_func(**args) if args else global_func()
        except Exception as e:
            return f"Error executing {name}: {e}"
    return f"Unknown function: {name}"
