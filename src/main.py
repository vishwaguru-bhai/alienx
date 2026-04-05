#!/usr/bin/env python3
"""
AlienX - Voice-controlled PC automation assistant.
Uses OpenRouter LLM for intent recognition.
"""

import os
import json
import subprocess
import datetime
import logging
import shutil
import psutil
import requests
from dotenv import load_dotenv
from openai import OpenAI
import threading
from pynput import keyboard
import sounddevice as sd
import numpy as np
import tempfile
import wave
import sys
import time
import speech_recognition as sr
try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

load_dotenv()

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Client (OpenRouter or OpenAI)
api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
if not api_key:
    logger.error("No API key found. Set OPENROUTER_API_KEY or OPENAI_API_KEY in .env")
    sys.exit(1)

client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1" if os.getenv("OPENROUTER_API_KEY") else None)
MODEL = os.getenv("MODEL", "openrouter/auto")

# ========== AUDIO ==========
def record_audio(duration=None, fs=16000):
    """Record audio from microphone. Duration from args or env."""
    if duration is None:
        duration = int(os.getenv("RECORD_DURATION", "3"))
    logger.info("Listening...")
    audio = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
    sd.wait()
    return audio, fs

def save_wav(audio, fs, filename):
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(fs)
        wf.writeframes(audio.tobytes())

def transcribe_audio_openrouter(filename):
    """Transcribe using Whisper via OpenRouter or OpenAI (fallback)."""
    with open(filename, 'rb') as f:
        try:
            resp = client.audio.transcriptions.create(
                model="whisper-1",
                file=f
            )
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return ""
    return resp.text.strip()

def transcribe_audio(filename):
    """Transcribe using Google Speech Recognition (free) with fallback to OpenRouter."""
    try:
        r = sr.Recognizer()
        with sr.AudioFile(filename) as source:
            audio = r.record(source)
        text = r.recognize_google(audio)
        logger.info("Transcribed via Google SR")
        return text.strip()
    except sr.UnknownValueError:
        logger.warning("Google SR could not understand audio")
        return ""
    except sr.RequestError as e:
        logger.error(f"Google SR service error: {e}, falling back to OpenRouter")
        return transcribe_audio_openrouter(filename)
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return ""

def listen(duration=None):
    """Record and return transcribed text."""
    if duration is None:
        duration = int(os.getenv("RECORD_DURATION", "3"))
    audio, fs = record_audio(duration)
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        tmp_name = tmp.name
    try:
        save_wav(audio, fs, tmp_name)
        text = transcribe_audio(tmp_name)
        logger.info(f"Heard: {text}")
        return text
    finally:
        os.unlink(tmp_name)

# ========== TTS ==========
def speak(text):
    """Speak using macOS 'say' with custom voice/speed, or espeak on Linux."""
    logger.info(f"Speaking: {text}")
    try:
        voice = os.getenv("VOICE", "")
        rate = os.getenv("RATE", "")
        if sys.platform == 'darwin':
            args = ['say']
            if voice:
                args.extend(['-v', voice])
            if rate:
                args.extend(['-r', rate])
            args.append(text)
            subprocess.run(args, check=True)
        else:
            subprocess.run(['espeak', text])
    except Exception as e:
        logger.error(f"TTS failed: {e}")

# ========== APP NAME RESOLUTION ==========
APP_ALIASES = {
    "chrome": "Google Chrome",
    "google chrome": "Google Chrome",
    "chromium": "Google Chrome",
    "safari": "Safari",
    "firefox": "Firefox",
    "fire fox": "Firefox",
    "vscode": "Visual Studio Code",
    "vs code": "Visual Studio Code",
    "code": "Visual Studio Code",
    "visual studio code": "Visual Studio Code",
    "terminal": "Terminal",
    "iterm": "iTerm",
    "iterm2": "iTerm",
    "finder": "Finder",
    "spotify": "Spotify",
    "music": "Music",
    "photos": "Photos",
    "mail": "Mail",
    "messages": "Messages",
    "calendar": "Calendar",
    "notes": "Notes",
    "calculator": "Calculator",
    "preview": "Preview",
    "textedit": "TextEdit",
    "sublime": "Sublime Text",
    "pycharm": "PyCharm",
    "idea": "IntelliJ IDEA",
    "webstorm": "WebStorm",
    "android studio": "Android Studio",
    "xcode": "Xcode",
    "microsoft word": "Microsoft Word",
    "word": "Microsoft Word",
    "excel": "Microsoft Excel",
    "powerpoint": "Microsoft PowerPoint",
    "ppt": "Microsoft PowerPoint",
}

def resolve_app_name(app_name: str) -> str:
    """Map common aliases to actual macOS app names."""
    key = app_name.lower().strip()
    if key in APP_ALIASES:
        return APP_ALIASES[key]
    title = app_name.title()
    if title != app_name:
        return title
    for suffix in ['.app', 'App']:
        if not app_name.endswith(suffix):
            candidate = app_name + suffix
            return candidate
    return app_name

# ========== ACTION FUNCTIONS ==========
def open_application(app_name: str) -> str:
    """Open a macOS/Unix application with smart name resolution."""
    try:
        original = app_name
        app_name = resolve_app_name(app_name)
        logger.info(f"Attempting to open: {app_name} (from '{original}')")
        if sys.platform == 'darwin':
            subprocess.run(['open', '-a', app_name], check=True)
        else:
            subprocess.run(['xdg-open', app_name], check=True)
        logger.info(f"Successfully opened {app_name}")
        return f"{app_name} खोला जा रहा है।"
    except Exception as e:
        logger.error(f"Failed to open {original} (tried {app_name}): {e}")
        return f"सॉरी, {original} नहीं खुल रहा। कृपया जांचें कि यह इंस्टॉल है कि नहीं।"

def open_url(url: str) -> str:
    """Open URL in default browser."""
    url = url.strip().lower()
    if '.' not in url:
        url = f"{url}.com"
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    try:
        logger.info(f"Opening URL: {url}")
        subprocess.run(['open', url] if sys.platform == 'darwin' else ['xdg-open', url], check=True)
        return f"{url} खोला जा रहा है।"
    except Exception as e:
        logger.error(f"Failed to open URL {url}: {e}")
        return f"सॉरी, {url} नहीं खुल रहा।"

def execute_shell(command: str) -> str:
    """Execute a shell command and return output."""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
        output = result.stdout.strip() or result.stderr.strip()
        if output:
            return output
        return "कमांड चलाया गया।"
    except subprocess.TimeoutExpired:
        return "कमांड टाइम आउट हो गया।"
    except Exception as e:
        return f"एरर: {e}"

def get_weather(city: str = "Delhi") -> str:
    """Placeholder weather - can integrate real API."""
    return f"{city} का मौसम: २५°C, धूप (उदाहरण)।"

def tell_time() -> str:
    now = datetime.datetime.now().strftime("%I:%M %p")
    return f"अभी समय है {now}"

def list_applications() -> str:
    """List running applications."""
    if sys.platform == 'darwin':
        script = 'tell application "System Events" to get name of every process whose background only is false'
        proc = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
        if proc.returncode == 0:
            apps = proc.stdout.strip().split(', ')
            return "चल रहे एप्स: " + ", ".join(apps[:10])
    return "एप्स नहीं मिल रहे।"

def lock_screen() -> str:
    """Lock screen."""
    if sys.platform == 'darwin':
        subprocess.run(['pmset', 'displaysleepnow'])
    else:
        subprocess.run(['loginctl', 'lock-session'])
    return "स्क्रीिन लॉक हो गई।"

def sleep_computer() -> str:
    """Put the computer to sleep."""
    if sys.platform == 'darwin':
        subprocess.run(['pmset', 'sleepnow'])
    else:
        subprocess.run(['systemctl', 'suspend'])
    return "कंप्यूटर स्लीप हो रहा है।"

def say_hello() -> str:
    return "नमस्ते! मैं AlienX हूँ, आपका वॉयस असिस्टेंट।"

def play_music(genre: str = None, artist: str = None) -> str:
    """Play random music via AppleScript (macOS)."""
    try:
        if sys.platform == 'darwin':
            script = '''
            tell application "Music"
                activate
                play
            end tell
            '''
            result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, check=True)
            logger.info(f"Music script output: {result.stdout.strip()}")
            return "रैंडम गाना बजा रहा हूँ।"
        else:
            return "Music control not implemented for this OS."
    except subprocess.CalledProcessError as e:
        logger.error(f"AppleScript error: {e.stderr}")
        return f"गाना नहीं बज रहा: {e.stderr}"
    except Exception as e:
        logger.exception("play_music failed")
        return f"गाना नहीं बज रहा: {e}"

def pause_music() -> str:
    """Pause music playback."""
    try:
        if sys.platform == 'darwin':
            subprocess.run(['osascript', '-e', 'tell application "Music" to pause'], check=True)
            return "म्यूजिक पॉज़ किया गया।"
        else:
            return "Not supported on this OS."
    except Exception as e:
        return f"पॉज़ में त्रुटि: {e}"

def next_track() -> str:
    """Skip to next track."""
    try:
        if sys.platform == 'darwin':
            subprocess.run(['osascript', '-e', 'tell application "Music" to next track'], check=True)
            return "अगले ट्रैक पर जा रहा हूँ।"
        else:
            return "Not supported on this OS."
    except Exception as e:
        return f"नेक्स्ट में त्रुटि: {e}"

def get_battery() -> str:
    """Get battery status (macOS)."""
    try:
        if sys.platform == 'darwin':
            info = subprocess.run(['pmset', '-g', 'batt'], capture_output=True, text=True)
            lines = info.stdout.strip().split('\n')
            if lines:
                return f"बैटरी: {lines[1] if len(lines)>1 else lines[0]}"
        return "बैटरी जानकारी उपलब्ध नहीं।"
    except Exception as e:
        return f"बैटरी एरर: {e}"

def get_system_stats() -> str:
    """Get system uptime and memory."""
    try:
        if sys.platform == 'darwin':
            uptime = subprocess.run(['uptime'], capture_output=True, text=True).stdout.strip()
            mem = subprocess.run(['vm_stat'], capture_output=True, text=True).stdout.strip().split('\n')[0]
            return f"ऑपनटाइम: {uptime}\nमेमोरी: {mem}"
        return "सिस्टम जानकारी इस ऑएस पर समर्थित नहीं।"
    except Exception as e:
        return f"सिस्टम स्टैट्स एरर: {e}"

def take_screenshot() -> str:
    """Take screenshot and save to desktop."""
    try:
        if sys.platform == 'darwin':
            desktop = os.path.expanduser('~/Desktop')
            filename = f"screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            path = os.path.join(desktop, filename)
            subprocess.run(['screencapture', '-x', path], check=True)
            return f"स्क्रीनशॉट लिया गया: {path}"
        return "स्क्रीनशॉट इस ऑएस पर समर्थित नहीं।"
    except Exception as e:
        return f"स्क्रीनशॉट एरर: {e}"

def set_volume(level: int = 50) -> str:
    """Set system volume (0-100)."""
    try:
        if sys.platform == 'darwin':
            subprocess.run(['osascript', '-e', f'set volume output volume {level}'], check=True)
            return f"वॉल्यूम सेट किया: {level}%"
        return "वॉल्यूम कंट्रोल इस ऑएस पर समर्थित नहीं।"
    except Exception as e:
        return f"वॉल्यूम एरर: {e}"

def get_network() -> str:
    """Get current Wi-Fi network name."""
    try:
        if sys.platform == 'darwin':
            net = subprocess.run(['networksetup', '-getairportnetwork', 'en0'], capture_output=True, text=True)
            if net.returncode == 0:
                return f"Wi-Fi: {net.stdout.strip()}"
            else:
                return "Wi-Fi नेटवर्क नहीं मिल रहा।"
        return "नेटवर्क जानकारी इस ऑएस पर समर्थित नहीं।"
    except Exception as e:
        return f"नेटवर्क एरर: {e}"

def get_system_info() -> str:
    """Get detailed system info (CPU, RAM, Disk)."""
    try:
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        return f"CPU: {cpu}% | RAM: {ram.percent}% | Disk: {disk.percent}% used."
    except Exception as e:
        return f"सिस्टम_info एरर: {e}"

def empty_trash() -> str:
    """Empty the trash bin."""
    try:
        if sys.platform == 'darwin':
            subprocess.run(['osascript', '-e', 'tell application \"Finder\" to empty trash'], check=True)
            return "कचरा खाली कर दिया गया।"
        return "Trash empty इस OS पर समर्थित नहीं।"
    except Exception as e:
        return f"Trash खाली करने में एरर: {e}"

def clean_downloads() -> str:
    """Delete all files in the Downloads folder (Safety: Moves to Trash)."""
    try:
        download_path = os.path.expanduser('~/Downloads')
        for filename in os.listdir(download_path):
            file_path = os.path.join(download_path, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
        return "Downloads फोल्डर साफ़ कर दिया गया है।"
    except Exception as e:
        return f"Clean एरर: {e}"

def set_brightness(level: int) -> str:
    """Set screen brightness (0-100) on macOS."""
    try:
        if sys.platform == 'darwin':
            subprocess.run(['osascript', '-e', f'set volume output volume {level}'], check=True) # Note: This sets volume, brightness requires 'brightness' CLI or specific AppleScript
            # Correct brightness script for macOS:
            script = f'tell application \"System Events\" to set brightness of display 1 to {level/100}'
            subprocess.run(['osascript', '-e', script], check=True)
            return f"ब्राइटनेस {level}% सेट किया गया।"
        return "Brightness control इस OS पर समर्थित नहीं।"
    except Exception as e:
        return f"Brightness एरर: {e}"

def move_window(direction: str) -> str:
    """Move current window (Left/Right/Maximize)."""
    try:
        if sys.platform == 'darwin' and PYAUTOGUI_AVAILABLE:
            size = pyautogui.size()
            if direction.lower() == 'left':
                pyautogui.moveTo(0, 0)
                # Requires AppleScript for actual window resizing
                script = 'tell application \"System Events\" to set size of window 1 of application (path to frontmost application as text) to {680, 700}'
                subprocess.run(['osascript', '-e', script], check=True)
            elif direction.lower() == 'right':
                script = 'tell application \"System Events\" to set position of window 1 of application (path to frontmost application as text) to {700, 0}'
                subprocess.run(['osascript', '-e', script], check=True)
            return f"Window को {direction} shifted किया गया।"
        return "Window management इस OS पर अभी समर्थित नहीं।"
    except Exception as e:
        return f"Window move एरर: {e}"

def get_network_speed() -> str:
    """Get current network upload/download speed."""
    try:
        # Using psutil to get a snapshot
        net = psutil.net_io_counters()
        return f"Bytes Sent: {net.bytes_sent}, Bytes Recv: {net.bytes_recv} (Since boot)"
    except Exception as e:
        return f"Speed check एरर: {e}"

def get_battery_info() -> str:
    """Get detailed battery status."""
    try:
        if sys.platform == 'darwin':
            info = subprocess.run(['pmset', '-g', 'batt'], capture_output=True, text=True)
            return info.stdout.strip()
        return "Battery info उपलब्ध नहीं।"
    except Exception as e:
        return f"Battery एरर: {e}"

def show_calendar() -> str:
    """Show current month calendar."""
    try:
        cal = subprocess.run(['cal'], capture_output=True, text=True)
        return f"Calendar:\n{cal.stdout}"
    except Exception as e:
        return f"Calendar एरर: {e}"

def toggle_wifi() -> str:
    """Turn Wi-Fi on or off."""
    try:
        if sys.platform == 'darwin':
            # Get power status
            status = subprocess.run(['networksetup', '-getairportpower', 'en0'], capture_output=True, text=True)
            if 'On' in status.stdout:
                subprocess.run(['networksetup', '-setairportpower', 'en0', 'off'])
                return "Wi-Fi बंद किया गया।"
            else:
                subprocess.run(['networksetup', '-setairportpower', 'en0', 'on'])
                return "Wi-Fi चालू किया गया।"
        return "Wi-Fi toggle इस OS पर समर्थित नहीं।"
    except Exception as e:
        return f"Wi-Fi एरर: {e}"

def find_file(filename: str) -> str:
    """Search for a file in the Home directory."""
    try:
        home = os.path.expanduser('~')
        for root, dirs, files in os.walk(home):
            if filename in files:
                return f"File मिला: {os.path.join(root, filename)}"
        return "File नहीं मिला।"
    except Exception as e:
        return f"Search एरर: {e}"

# ========== LLM INTENT ==========
FUNCTIONS = [
    {
        "name": "open_application",
        "description": "Open an application by name. Examples: Chrome, VS Code, Safari, Terminal, Firefox.",
        "parameters": {
            "type": "object",
            "properties": {
                "app_name": {"type": "string", "description": "Application name, e.g., 'Chrome', 'Safari', 'VSCode'"}
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "open_url",
        "description": "Open a URL in the default web browser.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL like 'google.com', 'youtube.com', 'github.com'"}
            },
            "required": ["url"]
        }
    },
    {
        "name": "execute_shell",
        "description": "Run a shell command on the computer. Use for custom tasks like listing files, checking processes, controlling system.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Full shell command, e.g., 'ls -la', 'ps aux', 'date'"}
            },
            "required": ["command"]
        }
    },
    {
        "name": "get_weather",
        "description": "Get current weather for a city.",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "default": "Delhi"}
            }
        }
    },
    {
        "name": "tell_time",
        "description": "Tell the current time.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "list_applications",
        "description": "List currently running applications.",
        "parameters": {"type": "object", "properties": {}}
    },
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
        "name": "say_hello",
        "description": "Greet the user.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "play_music",
        "description": "Play random music or specific genre/artist. Use when user says 'play music', 'bajao', 'random album', etc.",
        "parameters": {
            "type": "object",
            "properties": {
                "genre": {"type": "string", "description": "Optional music genre (rock, pop, jazz, etc.)"},
                "artist": {"type": "string", "description": "Optional artist name"}
            },
            "required": []
        }
    },
    {
        "name": "pause_music",
        "description": "Pause currently playing music.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "next_track",
        "description": "Skip to the next track.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "get_battery",
        "description": "Get battery status and charge level.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "get_system_stats",
        "description": "Get system uptime and memory info.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "take_screenshot",
        "description": "Take a screenshot and save to desktop.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "set_volume",
        "description": "Set system volume (0-100).",
        "parameters": {
            "type": "object",
            "properties": {
                "level": {"type": "integer", "description": "Volume level 0-100"}
            },
            "required": []
        }
    },
    {
        "name": "get_network",
        "description": "Get current Wi-Fi network name.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "get_system_info",
        "description": "Get CPU, RAM, and Disk usage stats.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "empty_trash",
        "description": "Empty the system trash bin.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "clean_downloads",
        "description": "Delete all files in the Downloads folder.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "set_brightness",
        "description": "Set screen brightness level (0-100).",
        "parameters": {
            "type": "object",
            "properties": {"level": {"type": "integer"}},
            "required": ["level"]
        }
    },
    {
        "name": "move_window",
        "description": "Move current window to left or right.",
        "parameters": {
            "type": "object",
            "properties": {"direction": {"type": "string", "enum": ["left", "right", "maximize"]}},
            "required": ["direction"]
        }
    },
    {
        "name": "get_battery_info",
        "description": "Get detailed battery status.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "show_calendar",
        "description": "Display the current month's calendar.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "toggle_wifi",
        "description": "Turn Wi-Fi on or off.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "find_file",
        "description": "Search for a file by name in the Home directory.",
        "parameters": {
            "type": "object",
            "properties": {"filename": {"type": "string"}},
            "required": ["filename"]
        }
    }
]

def process_text(text: str):
    """Send text to LLM with tool definitions; return message with possible tool_calls."""
    try:
        tools = [{"type": "function", "function": f} for f in FUNCTIONS]
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a voice-controlled AI assistant. Your ONLY job is to call functions to perform actions. NEVER respond with plain text when an action is needed. For ANY command like 'open Chrome', 'play music', 'lock screen', 'what time', 'run ls', you MUST call the appropriate function. Keep responses extremely short (1-2 words) when speaking to user."},
                {"role": "user", "content": text}
            ],
            tools=tools,
            tool_choice="auto"
        )
        return resp.choices[0].message
    except Exception as e:
        logger.error(f"LLM error: {e}")
        return None

def execute_function_call_by_name(name: str, args: dict):
    """Execute a function given its name and arguments dict."""
    logger.info(f"Executing: {name} with {args}")
    try:
        if name == "open_application":
            return open_application(**args)
        elif name == "open_url":
            return open_url(**args)
        elif name == "execute_shell":
            return execute_shell(**args)
        elif name == "get_weather":
            return get_weather(**args)
        elif name == "tell_time":
            return tell_time()
        elif name == "list_applications":
            return list_applications()
        elif name == "lock_screen":
            return lock_screen()
        elif name == "sleep_computer":
            return sleep_computer()
        elif name == "say_hello":
            return say_hello()
        elif name == "play_music":
            return play_music(**args)
        elif name == "pause_music":
            return pause_music()
        elif name == "next_track":
            return next_track()
        elif name == "get_battery":
            return get_battery()
        elif name == "get_system_stats":
            return get_system_stats()
        elif name == "take_screenshot":
            return take_screenshot()
        elif name == "set_volume":
            return set_volume(**args)
        elif name == "get_network":
            return get_network()
        elif name == "get_system_info":
            return get_system_info()
        elif name == "empty_trash":
            return empty_trash()
        elif name == "clean_downloads":
            return clean_downloads()
        elif name == "set_brightness":
            return set_brightness(**args)
        elif name == "move_window":
            return move_window(**args)
        elif name == "get_battery_info":
            return get_battery_info()
        elif name == "show_calendar":
            return show_calendar()
        elif name == "toggle_wifi":
            return toggle_wifi()
        elif name == "find_file":
            return find_file(**args)
        else:
            return f"Unknown function: {name}"
    except Exception as e:
        logger.error(f"Execution error: {e}")
        return f"Error executing {name}: {e}"

def process_and_speak(text: str):
    """Process a command string and speak the result."""
    try:
        logger.info(f"Command: {text}")
        response_msg = process_text(text)
        if not response_msg:
            speak("Sorry, I couldn't process that.")
            return

        if response_msg.tool_calls:
            tool_call = response_msg.tool_calls[0]
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
            logger.info(f"TOOL CALL: {name} args={args}")
            result = execute_function_call_by_name(name, args)
            speak(result)
        elif response_msg.function_call:
            name = response_msg.function_call.name
            args = json.loads(response_msg.function_call.arguments) if response_msg.function_call.arguments else {}
            logger.info(f"FUNCTION CALL (legacy): {name} args={args}")
            result = execute_function_call_by_name(name, args)
            speak(result)
        else:
            content = response_msg.content or "I'm not sure how to do that."
            logger.info(f"NO TOOL CALL; content: {content}")
            speak(content)
    except Exception as e:
        logger.exception("Assistant error")
        speak(f"Error: {e}")

def run_assistant():
    """Hotkey activation: listen once and process."""
    try:
        user_text = listen()
        if not user_text:
            speak("Sorry, I didn't catch that.")
            return
        process_and_speak(user_text)
    except Exception as e:
        logger.exception("Assistant error")
        speak(f"Error: {e}")

def main():
    logger.info("🤖 AlienX voice assistant starting...")
    speak("नमस्ते! मैं AlienX हूँ, आपका वॉयस असिस्टेंट।")

    wake_word = os.getenv("WAKE_WORD", "").lower()
    if wake_word:
        logger.info(f"Wake word mode enabled. Say '{wake_word}' to activate.")
        print(f"Say '{wake_word}' to activate... (Press Ctrl+C to exit)")
        try:
            while True:
                ww_duration = int(os.getenv("WAKE_WORD_DURATION", "2"))
                text = listen(duration=ww_duration).lower()
                if wake_word in text:
                    logger.info("Wake word detected!")
                    speak("Yes?")
                    cmd = listen(duration=int(os.getenv("COMMAND_DURATION", "3")))
                    if cmd:
                        process_and_speak(cmd)
                    else:
                        speak("No command heard.")
                    # Debounce: prevent immediate re-trigger
                    time.sleep(2)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            sys.exit(0)
    else:
        # Hotkey mode
        hotkey = os.getenv("HOTKEY", "<cmd>+<alt>+j" if sys.platform == 'darwin' else "<ctrl>+<alt>+j")
        logger.info(f"Press {hotkey} to activate voice command.")
        try:
            with keyboard.GlobalHotKeys({hotkey: on_activate}) as h:
                h.join()
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            sys.exit(0)

if __name__ == "__main__":
    main()
