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
    ACTIVE_TIMEOUT = 15  # seconds to stay awake after interaction

    if WAKE_WORD:
        logger.info(f"Smart Wake mode enabled. Say '{WAKE_WORD}' to activate.")
        print(f"Say '{WAKE_WORD}' to activate... (Press Ctrl+C to exit)")
        try:
            while True:
                last_active = time.time() - (ACTIVE_TIMEOUT + 10)  # Start in sleep mode
                
                # Check if we should listen for wake word or command
                current_time = time.time()
                is_active = (current_time - last_active) < ACTIVE_TIMEOUT
                
                duration = 2 if is_active else int(os.getenv("WAKE_WORD_DURATION", "2"))
                text = listen(duration=duration).lower()
                
                if not text:
                    continue

                # Wake word detection or Active Window Logic
                if WAKE_WORD in text or is_active:
                    if WAKE_WORD in text and not is_active:
                        logger.info("Wake word detected! Activating...")
                        speak("Haan boss?")
                        last_active = time.time()
                        time.sleep(0.5) # Chhota sa pause taaki echo na aaye
                        continue 
                    
                    # Process Command
                    if WAKE_WORD in text and not is_active:
                        # Agar wake word abhi detect hua hai, toh command ke liye thoda wait karo
                        time.sleep(0.5)
                        
                    # Agar active window mein hain ya abhi wake hua hai
                    cmd_duration = int(os.getenv("COMMAND_DURATION", "4"))
                    command_text = listen(duration=cmd_duration).lower()
                    
                    if command_text:
                        logger.info(f"Processing: {command_text}")
                        process_and_speak(command_text, speak)
                        last_active = time.time() # Reset timer on interaction
                    else:
                        if is_active:
                            logger.info("No command heard in active window. Going to sleep.")
                        last_active = time.time() - (ACTIVE_TIMEOUT + 10) # Force sleep if wake word failed

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
