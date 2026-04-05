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

def listen():
    """Record and return transcribed text."""
    audio, fs = record_audio()
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
    """Speak using macOS 'say' or espeak on Linux."""
    logger.info(f"Speaking: {text}")
    try:
        if sys.platform == 'darwin':
            subprocess.run(['say', text])
        else:
            subprocess.run(['espeak', text])
    except Exception as e:
        logger.error(f"TTS failed: {e}")

# ========== ACTION FUNCTIONS ==========
def open_application(app_name: str) -> str:
    """Open a macOS/Unix application."""
    try:
        logger.info(f"Attempting to open: {app_name}")
        if sys.platform == 'darwin':
            subprocess.run(['open', '-a', app_name], check=True)
        else:
            subprocess.run(['xdg-open', app_name], check=True)
        logger.info(f"Successfully opened {app_name}")
        return f"Opening {app_name}."
    except Exception as e:
        logger.error(f"Failed to open {app_name}: {e}")
        return f"Failed to open {app_name}: {e}"

def open_url(url: str) -> str:
    """Open URL in default browser."""
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    try:
        subprocess.run(['open', url] if sys.platform == 'darwin' else ['xdg-open', url], check=True)
        return f"Opening {url}."
    except Exception as e:
        return f"Failed to open URL: {e}"

def execute_shell(command: str) -> str:
    """Execute a shell command and return output."""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
        output = result.stdout.strip() or result.stderr.strip()
        return output if output else "Command executed."
    except subprocess.TimeoutExpired:
        return "Command timed out."
    except Exception as e:
        return f"Error: {e}"

def get_weather(city: str = "Delhi") -> str:
    """Placeholder weather - can integrate real API."""
    return f"Weather for {city}: 25°C, sunny (sample)."

def tell_time() -> str:
    now = datetime.datetime.now().strftime("%I:%M %p")
    return f"The time is {now}."

def list_applications() -> str:
    """List running applications."""
    if sys.platform == 'darwin':
        script = 'tell application "System Events" to get name of every process whose background only is false'
        proc = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
        if proc.returncode == 0:
            apps = proc.stdout.strip().split(', ')
            return "Running apps: " + ", ".join(apps[:10])
    return "Could not fetch apps."

def lock_screen() -> str:
    """Lock screen."""
    if sys.platform == 'darwin':
        subprocess.run(['pmset', 'displaysleepnow'])
    else:
        subprocess.run(['loginctl', 'lock-session'])
    return "Screen locked."

def sleep_computer() -> str:
    """Put computer to sleep."""
    if sys.platform == 'darwin':
        subprocess.run(['pmset', 'sleepnow'])
    else:
        subprocess.run(['systemctl', 'suspend'])
    return "Computer going to sleep."

def say_hello() -> str:
    return "Hello! I'm AlienX, your voice assistant."

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
            return "Playing random music."
        else:
            return "Music control not implemented for this OS."
    except subprocess.CalledProcessError as e:
        logger.error(f"AppleScript error: {e.stderr}")
        return f"Could not play music: {e.stderr}"
    except Exception as e:
        logger.exception("play_music failed")
        return f"Could not play music: {e}"

def pause_music() -> str:
    """Pause music playback."""
    try:
        if sys.platform == 'darwin':
            subprocess.run(['osascript', '-e', 'tell application "Music" to pause'], check=True)
            return "Music paused."
        else:
            return "Not supported on this OS."
    except Exception as e:
        return f"Error pausing: {e}"

def next_track() -> str:
    """Skip to next track."""
    try:
        if sys.platform == 'darwin':
            subprocess.run(['osascript', '-e', 'tell application "Music" to next track'], check=True)
            return "Skipped to next track."
        else:
            return "Not supported on this OS."
    except Exception as e:
        return f"Error skipping: {e}"

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
    """Send text to LLM with function definitions; return function call or text response."""
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a voice-controlled AI assistant. Your ONLY job is to call functions to perform actions. NEVER respond with plain text when an action is needed. For ANY command like 'open Chrome', 'play music', 'lock screen', 'what time', 'run ls', you MUST call the appropriate function. Keep responses extremely short (1-2 words) when speaking to user."},
                {"role": "user", "content": text}
            ],
            functions=FUNCTIONS,
            function_call={"name": "any"}  # Force function call
        )
        return resp.choices[0].message
    except Exception as e:
        logger.error(f"LLM error: {e}")
        return None

def execute_function_call(msg):
    if not msg or not msg.function_call:
        return msg.content if msg else "I didn't understand."
    name = msg.function_call.name
    args = json.loads(msg.function_call.arguments) if msg.function_call.arguments else {}
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

def run_assistant():
    try:
        user_text = listen()
        if not user_text:
            speak("Sorry, I didn't catch that.")
            return
        logger.info(f"Command: {user_text}")
        response_msg = process_text(user_text)
        if not response_msg:
            speak("Sorry, I couldn't process that.")
            return
        # DEBUG: print function call details
        if response_msg.function_call:
            logger.info(f"FUNCTION CALL: {response_msg.function_call.name} args={response_msg.function_call.arguments}")
        else:
            logger.info(f"NO FUNCTION CALL; content: {response_msg.content}")
        result = execute_function_call(response_msg)
        speak(result)
    except Exception as e:
        logger.exception("Assistant error")
        speak(f"Error: {e}")

def main():
    logger.info("🤖 AlienX voice assistant starting...")
    speak("AlienX online.")
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
