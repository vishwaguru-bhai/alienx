import os
import sys
import subprocess
import datetime
import logging
import psutil
import json
import inspect

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
    "vscode": "Visual Studio Code",
    "terminal": "Terminal",
    "safari": "Safari",
    "firefox": "Firefox",
    "spotify": "Spotify",
    "slack": "Slack",
    "zoom": "Zoom",
    "notes": "Notes",
    "finder": "Finder",
    "mail": "Mail",
    "messages": "Messages",
    "whatsapp": "WhatsApp",
}

def resolve_app_name(app_name: str) -> str:
    key = app_name.lower().strip()
    return APP_ALIASES.get(key, app_name.title())


# ========== 1. MISSING FUNCTIONS (migrated from temp.py) ==========

def open_application(app_name: str) -> str:
    try:
        app_name = resolve_app_name(app_name)
        if sys.platform == 'darwin':
            subprocess.run(['open', '-a', app_name], check=True)
        else:
            subprocess.run(['xdg-open', app_name], check=True)
        return f"{app_name} khola ja raha hai."
    except Exception as e:
        return f"Sorry, {app_name} nahi khul raha."

def open_url(url: str) -> str:
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    try:
        cmd = ['open', url] if sys.platform == 'darwin' else ['xdg-open', url]
        subprocess.run(cmd, check=True)
        return f"{url} browser mein khul raha hai."
    except Exception as e:
        return f"URL nahi khul raha: {e}"

def execute_shell(command: str) -> str:
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
        output = result.stdout.strip() or result.stderr.strip()
        return output if output else "Command execute ho gaya."
    except subprocess.TimeoutExpired:
        return "Command timeout ho gayi."
    except Exception as e:
        return f"Error: {e}"

def tell_time() -> str:
    now = datetime.datetime.now().strftime("%I:%M %p")
    return f"Abhi {now} baj rahe hain."

def tell_date() -> str:
    now = datetime.datetime.now().strftime("%A, %d %B %Y")
    return f"Aaj {now} hai."

def lock_screen() -> str:
    try:
        if sys.platform == 'darwin':
            subprocess.run(['pmset', 'displaysleepnow'])
        else:
            subprocess.run(['loginctl', 'lock-session'])
        return "Screen lock ho gayi."
    except Exception as e:
        return f"Lock error: {e}"

def sleep_computer() -> str:
    try:
        if sys.platform == 'darwin':
            subprocess.run(['pmset', 'sleepnow'])
        else:
            subprocess.run(['systemctl', 'suspend'])
        return "Computer so raha hai."
    except Exception as e:
        return f"Sleep error: {e}"

def list_applications() -> str:
    try:
        if sys.platform == 'darwin':
            script = 'tell application "System Events" to get name of every process whose background only is false'
            proc = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
            if proc.returncode == 0:
                apps = proc.stdout.strip().split(', ')
                return "Chal rahe apps: " + ", ".join(apps[:10])
        return "Apps nahi milе."
    except Exception as e:
        return f"Error: {e}"


# ========== 2. QUICK WINS ==========

def set_volume(level: int) -> str:
    try:
        level = max(0, min(100, level))
        if sys.platform == 'darwin':
            subprocess.run(['osascript', '-e', f'set volume output volume {level}'], check=True)
            return f"Volume {level}% ho gayi."
        else:
            subprocess.run(['amixer', '-D', 'pulse', 'sset', 'Master', f'{level}%'], check=True)
            return f"Volume {level}% ho gayi."
    except Exception as e:
        return f"Volume error: {e}"

def mute_volume() -> str:
    try:
        if sys.platform == 'darwin':
            subprocess.run(['osascript', '-e', 'set volume output muted true'], check=True)
        else:
            subprocess.run(['amixer', '-D', 'pulse', 'sset', 'Master', 'mute'])
        return "Mute ho gaya."
    except Exception as e:
        return f"Mute error: {e}"

def unmute_volume() -> str:
    try:
        if sys.platform == 'darwin':
            subprocess.run(['osascript', '-e', 'set volume output muted false'], check=True)
        else:
            subprocess.run(['amixer', '-D', 'pulse', 'sset', 'Master', 'unmute'])
        return "Unmute ho gaya."
    except Exception as e:
        return f"Unmute error: {e}"

def take_screenshot() -> str:
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        desktop = os.path.expanduser(f"~/Desktop/screenshot_{timestamp}.png")
        if sys.platform == 'darwin':
            subprocess.run(['screencapture', '-x', desktop], check=True)
        else:
            subprocess.run(['scrot', desktop], check=True)
        return f"Screenshot le liya: {desktop}"
    except Exception as e:
        return f"Screenshot error: {e}"

def get_battery_info() -> str:
    try:
        battery = psutil.sensors_battery()
        if battery is None:
            return "Battery sensor nahi mila."
        percent = battery.percent
        plugged = "charging" if battery.power_plugged else "not charging"
        return f"Battery {percent:.0f}% hai, {plugged}."
    except Exception as e:
        return f"Battery info error: {e}"

def get_clipboard() -> str:
    try:
        if sys.platform == 'darwin':
            result = subprocess.run(['pbpaste'], capture_output=True, text=True)
            text = result.stdout.strip()
            return f"Clipboard mein hai: {text[:100]}" if text else "Clipboard khaali hai."
        return "Clipboard not supported."
    except Exception as e:
        return f"Clipboard error: {e}"

def music_control(action: str) -> str:
    """Control Spotify or Apple Music. action: play, pause, next, previous"""
    try:
        if sys.platform == 'darwin':
            action_map = {
                "play": "play",
                "pause": "pause",
                "next": "next track",
                "previous": "previous track",
                "stop": "pause",
            }
            act = action_map.get(action.lower(), "play")
            # Try Spotify first, then Music
            for app in ["Spotify", "Music"]:
                result = subprocess.run(
                    ['osascript', '-e', f'tell application "{app}" to {act}'],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    return f"{app}: {action} ho gaya."
            return "Spotify ya Music nahi chal raha."
        return "Music control not supported."
    except Exception as e:
        return f"Music error: {e}"


# ========== 3. MEDIUM FEATURES ==========

def send_notification(title: str, message: str) -> str:
    try:
        if sys.platform == 'darwin':
            script = f'display notification "{message}" with title "{title}"'
            subprocess.run(['osascript', '-e', script], check=True)
            return f"Notification bhej di: {title}"
        return "Notifications not supported."
    except Exception as e:
        return f"Notification error: {e}"

def get_weather(city: str = "Delhi") -> str:
    try:
        import urllib.request
        url = f"https://wttr.in/{city.replace(' ', '+')}?format=3"
        req = urllib.request.Request(url, headers={"User-Agent": "curl/7.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.read().decode().strip()
    except Exception as e:
        return f"{city} ka mausam nahi mila: {e}"

def find_file(filename: str) -> str:
    try:
        if sys.platform == 'darwin':
            result = subprocess.run(
                ['mdfind', '-name', filename],
                capture_output=True, text=True, timeout=5
            )
            files = result.stdout.strip().split('\n')
            files = [f for f in files if f][:5]
            if files:
                return "Mila: " + " | ".join(files)
            return f"'{filename}' nahi mila."
        else:
            result = subprocess.run(
                ['find', os.path.expanduser('~'), '-name', f'*{filename}*', '-maxdepth', '5'],
                capture_output=True, text=True, timeout=5
            )
            files = result.stdout.strip().split('\n')[:5]
            return "Mila: " + " | ".join(f for f in files if f) if files[0] else f"'{filename}' nahi mila."
    except Exception as e:
        return f"File search error: {e}"

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
            return "Trash khaali kar diya."
        return "Not supported."
    except Exception as e:
        return f"Error: {e}"

def clean_downloads() -> str:
    try:
        download_path = os.path.expanduser('~/Downloads')
        count = 0
        for filename in os.listdir(download_path):
            file_path = os.path.join(download_path, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
                count += 1
        return f"Downloads folder saaf kar diya. {count} files delete kiye."
    except Exception as e:
        return f"Error: {e}"

def set_brightness(level: int) -> str:
    try:
        if sys.platform == 'darwin':
            script = f'tell application "System Events" to set brightness of display 1 to {level/100}'
            subprocess.run(['osascript', '-e', script], check=True)
            return f"Brightness {level}% ho gayi."
        return "Not supported."
    except Exception as e:
        return f"Brightness error: {e}"

def toggle_wifi() -> str:
    try:
        if sys.platform == 'darwin':
            status = subprocess.run(['networksetup', '-getairportpower', 'en0'], capture_output=True, text=True)
            state = 'off' if 'On' in status.stdout else 'on'
            subprocess.run(['networksetup', '-setairportpower', 'en0', state])
            return f"Wi-Fi {state} ho gayi."
        return "Not supported."
    except Exception as e:
        return f"Wi-Fi error: {e}"


# ========== FUNCTION DEFINITIONS FOR LLM ==========
FUNCTIONS = [
    # --- App & Web ---
    {
        "name": "open_application",
        "description": "Open an application by name. E.g. Chrome, VS Code, Spotify, Terminal.",
        "parameters": {"type": "object", "properties": {"app_name": {"type": "string"}}, "required": ["app_name"]}
    },
    {
        "name": "open_url",
        "description": "Open a URL or website in the default browser. E.g. youtube.com, github.com.",
        "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}
    },
    # --- Shell ---
    {
        "name": "execute_shell",
        "description": "Run a shell/terminal command and return the output.",
        "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}
    },
    # --- Time & Date ---
    {
        "name": "tell_time",
        "description": "Tell the current time.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "tell_date",
        "description": "Tell today's date.",
        "parameters": {"type": "object", "properties": {}}
    },
    # --- System control ---
    {
        "name": "lock_screen",
        "description": "Lock the screen.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "sleep_computer",
        "description": "Put the computer to sleep.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "list_applications",
        "description": "List currently running applications.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "get_system_info",
        "description": "Get CPU, RAM, and Disk usage stats.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "get_battery_info",
        "description": "Get battery percentage and charging status.",
        "parameters": {"type": "object", "properties": {}}
    },
    # --- Volume ---
    {
        "name": "set_volume",
        "description": "Set system volume to a level between 0 and 100.",
        "parameters": {"type": "object", "properties": {"level": {"type": "integer", "minimum": 0, "maximum": 100}}, "required": ["level"]}
    },
    {
        "name": "mute_volume",
        "description": "Mute system audio.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "unmute_volume",
        "description": "Unmute system audio.",
        "parameters": {"type": "object", "properties": {}}
    },
    # --- Screenshot ---
    {
        "name": "take_screenshot",
        "description": "Take a screenshot and save it to the Desktop.",
        "parameters": {"type": "object", "properties": {}}
    },
    # --- Clipboard ---
    {
        "name": "get_clipboard",
        "description": "Read the current clipboard content.",
        "parameters": {"type": "object", "properties": {}}
    },
    # --- Music ---
    {
        "name": "music_control",
        "description": "Control Spotify or Apple Music. Actions: play, pause, next, previous.",
        "parameters": {"type": "object", "properties": {"action": {"type": "string", "enum": ["play", "pause", "next", "previous", "stop"]}}, "required": ["action"]}
    },
    # --- Notifications ---
    {
        "name": "send_notification",
        "description": "Send a macOS notification with a title and message.",
        "parameters": {"type": "object", "properties": {"title": {"type": "string"}, "message": {"type": "string"}}, "required": ["title", "message"]}
    },
    # --- Weather ---
    {
        "name": "get_weather",
        "description": "Get current weather for a city.",
        "parameters": {"type": "object", "properties": {"city": {"type": "string", "default": "Delhi"}}}
    },
    # --- File search ---
    {
        "name": "find_file",
        "description": "Search for a file by name on the computer using Spotlight (macOS) or find.",
        "parameters": {"type": "object", "properties": {"filename": {"type": "string"}}, "required": ["filename"]}
    },
    # --- Files & Storage ---
    {
        "name": "empty_trash",
        "description": "Empty the trash bin.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "clean_downloads",
        "description": "Delete all files in the Downloads folder.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "set_brightness",
        "description": "Set screen brightness (0-100).",
        "parameters": {"type": "object", "properties": {"level": {"type": "integer"}}, "required": ["level"]}
    },
    {
        "name": "toggle_wifi",
        "description": "Toggle Wi-Fi on or off.",
        "parameters": {"type": "object", "properties": {}}
    },
]

def execute_function_call_by_name(name: str, args: dict):
    logger.info(f"Executing: {name} with {args}")
    global_func = globals().get(name)
    if not global_func or not callable(global_func):
        return f"Unknown function: {name}"
    try:
        # Filter args to only what the function actually accepts
        sig = inspect.signature(global_func)
        valid_args = {k: v for k, v in args.items() if k in sig.parameters}
        if args and valid_args != args:
            logger.warning(f"Dropped invalid args for {name}: {set(args) - set(valid_args)}")
        return global_func(**valid_args)
    except Exception as e:
        return f"Error executing {name}: {e}"
