import sys
import subprocess
import logging
import os

logger = logging.getLogger(__name__)

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
