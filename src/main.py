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
from dotenv import load_dotenv
from openai import OpenAI
import threading
from pynput import keyboard
import sounddevice as sd
import numpy as np
import tempfile
import wave
import sys
import speech_recognition as sr

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
    """Record audio from microphone. Duration from env or default 5s."""
    if duration is None:
        duration = int(os.getenv("RECORD_DURATION", "5"))
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
    """Record and return transcribed text. Duration from args or env."""
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

# ========== ACTION FUNCTIONS ==========
# App name mapping for common aliases (macOS)
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
    # Direct alias match
    if key in APP_ALIASES:
        return APP_ALIASES[key]
    # Try title case (first letters capital)
    title = app_name.title()
    if title != app_name:
        return title
    # Try adding common suffixes
    for suffix in ['.app', 'App']:
        if not app_name.endswith(suffix):
            candidate = app_name + suffix
            # Could verify exists, but just return
            return candidate
    return app_name

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
    # Clean up common speech artifacts
    url = url.strip().lower()
    # If it's just a domain without TLD, add .com as guess
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
    """Put computer to sleep."""
    if sys.platform == 'darwin':
        subprocess.run(['pmset', 'sleepnow'])
    else:
        subprocess.run(['systemctl', 'suspend'])
    return "कंप्यूटर स्लीप हो रहा है।"

def say_hello() -> str:
    return "नमस्ते! मैं AlienX हूँ, आपका वॉयस असिस्टेंट।"

def play_music(genre: str = None, artist: str = None) -> str:
    """Play random music via AppleScript (macOS) or generic command."""
    try:
        if sys.platform == 'darwin':
            # Simple script: launch Music and play
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
    }
]

def process_text(text: str):
    """Send text to LLM with tool definitions; return message with possible tool_calls."""
    try:
        # Convert FUNCTIONS to OpenAI tools format
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
            return pause_music(**args)
        elif name == "next_track":
            return next_track(**args)
        else:
            return f"Unknown function: {name}"
    except Exception as e:
        logger.error(f"Execution error: {e}")
        return f"Error executing {name}: {e}"

# ========== HOTKEY & MAIN ==========
def on_activate():
    """Hotkey pressed — start listening."""
    logger.info("Hotkey activated, listening...")
    threading.Thread(target=run_assistant, daemon=True).start()

def process_and_speak(text: str):
    """Process a command string and speak the result."""
    try:
        logger.info(f"Command: {text}")
        response_msg = process_text(text)
        if not response_msg:
            speak("Sorry, I couldn't process that.")
            return

        # Check for tool_calls (OpenAI v1 style)
        if response_msg.tool_calls:
            tool_call = response_msg.tool_calls[0]  # use first
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
            logger.info(f"TOOL CALL: {name} args={args}")
            result = execute_function_call_by_name(name, args)
            speak(result)
        elif response_msg.function_call:
            # Legacy fallback
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
    speak("AlienX online.")

    wake_word = os.getenv("WAKE_WORD", "").lower()
    if wake_word:
        logger.info(f"Wake word mode enabled. Say '{wake_word}' to activate.")
        print(f"Say '{wake_word}' to activate... (Press Ctrl+C to exit)")
        try:
            while True:
                # Listen for wake word (short burst)
                text = listen(duration=1).lower()
                if wake_word in text:
                    logger.info("Wake word detected!")
                    speak("Yes?")
                    # Now listen for command
                    cmd = listen(duration=int(os.getenv("COMMAND_DURATION", "3")))
                    if cmd:
                        process_and_speak(cmd)
                    else:
                        speak("No command heard.")
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
