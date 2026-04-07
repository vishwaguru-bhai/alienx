#!/usr/bin/env python3
"""
AlienX - Voice-controlled PC automation assistant.
Modular Architecture.
"""

import os
import sys
import logging
import time
from pynput import keyboard
from src.config import HOTKEY, WAKE_WORD
from src.voice.recorder import listen
from src.ai.llm import process_and_speak
from src.utils.tts import speak

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def on_activate():
    """Hotkey activation: listen once and process."""
    try:
        user_text = listen()
        if not user_text:
            speak("Sorry, I didn't catch that.")
            return
        process_and_speak(user_text, speak)
    except Exception as e:
        logger.exception("Assistant error")
        speak(f"Error: {e}")

def main():
    logger.info("🤖 AlienX voice assistant starting...")
    speak("Namaste! Main AlienX hoon.")

    if WAKE_WORD:
        logger.info(f"Wake word mode enabled. Say '{WAKE_WORD}' to activate.")
        print(f"Say '{WAKE_WORD}' to activate... (Press Ctrl+C to exit)")
        try:
            while True:
                ww_duration = int(os.getenv("WAKE_WORD_DURATION", "2"))
                text = listen(duration=ww_duration).lower()
                if WAKE_WORD in text:
                    logger.info("Wake word detected!")
                    speak("Yes?")
                    cmd = listen(duration=int(os.getenv("COMMAND_DURATION", "3")))
                    if cmd:
                        process_and_speak(cmd, speak)
                    else:
                        speak("No command heard.")
                    time.sleep(2)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            sys.exit(0)
    else:
        # Hotkey mode
        logger.info(f"Press {HOTKEY} to activate voice command.")
        try:
            with keyboard.GlobalHotKeys({HOTKEY: on_activate}) as h:
                h.join()
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            sys.exit(0)

if __name__ == "__main__":
    main()
