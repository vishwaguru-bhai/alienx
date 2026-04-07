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
    speak("Friday aapki seva me hazir hai sir.")
    ACTIVE_TIMEOUT = 15  # seconds to stay awake after interaction

    if WAKE_WORD:
        logger.info(f"Smart Wake mode enabled. Say '{WAKE_WORD}' to activate.")
        print(f"Say '{WAKE_WORD}' to activate... (Press Ctrl+C to exit)")
        try:
            last_active = time.time() - (ACTIVE_TIMEOUT + 10)  # Start in sleep mode
            while True:
                # Check if we should listen for wake word or command
                current_time = time.time()
                is_active = (current_time - last_active) < ACTIVE_TIMEOUT

                duration = 2 if is_active else int(os.getenv("WAKE_WORD_DURATION", "2"))
                text = listen(duration=duration).lower()

                if not text:
                    continue

                # Wake word detection or Active Window Logic
                if WAKE_WORD in text or is_active:
                    # Case 1: Wake Word Detected (Sleep -> Active)
                    if WAKE_WORD in text and not is_active:
                        logger.info("Wake word detected! Activating...")
                        speak("Haan boss?")
                        last_active = time.time()
                        time.sleep(0.5)
                        continue # Loop ghumaao taaki next listening command pakde

                    # Case 2: Active Window (Already Awake)
                    # Agar text mein sirf wake word tha aur already active hain, toh naya command suno
                    final_command = text.replace(WAKE_WORD, "").strip() if WAKE_WORD in text else text

                    if not final_command:
                        logger.info("Active window: Waiting for command...")
                        cmd_duration = int(os.getenv("COMMAND_DURATION", "4"))
                        final_command = listen(duration=cmd_duration).lower()
                        logger.info(f"Raw Command Received: '{final_command}'")

                    if final_command and len(final_command) > 2:
                        logger.info(f"Processing Command: {final_command}")
                        try:
                            process_and_speak(final_command, speak)
                        except Exception as e:
                            logger.error(f"Failed to process command: {e}")
                            speak("Kuch gadbad ho gayi boss.")
                        last_active = time.time() # Reset timer on interaction
                    else:
                        logger.info(f"Empty or too short command ('{final_command}'). Going to sleep.")
                        last_active = time.time() - (ACTIVE_TIMEOUT + 10)

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
