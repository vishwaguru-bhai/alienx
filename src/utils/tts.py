import sys
import re
import subprocess
import logging
import os
import time
import tempfile
import shutil

logger = logging.getLogger(__name__)

DEFAULT_VOICE = "hi-IN-SwaraNeural"

_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "]+",
    flags=re.UNICODE
)

def _clean(text: str) -> str:
    text = _EMOJI_RE.sub("", text)
    # Replace smart quotes with plain ones
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    # Collapse multiple whitespace/newlines into single space
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def _is_hindi(text: str) -> bool:
    return bool(re.search(r'[\u0900-\u097F]', text))

def speak(text: str):
    logger.info(f"Speaking: {text}")
    text = _clean(text)
    if not text:
        return

    voice = os.getenv("TTS_VOICE", DEFAULT_VOICE)
    rate = os.getenv("TTS_RATE", "")

    edge_bin = shutil.which("edge-tts")
    if not edge_bin:
        if _is_hindi(text):
            logger.error("edge-tts not installed. Run: pip install edge-tts")
        else:
            _fallback_speak(text)
        return

    # Try edge-tts CLI with retry (server can be flaky)
    for attempt in range(3):
        tmp = tempfile.mktemp(suffix=".mp3")
        try:
            cmd = [edge_bin, "--voice", voice, "--text", text, "--write-media", tmp]
            if rate:
                cmd += ["--rate", rate]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if result.returncode == 0 and os.path.exists(tmp) and os.path.getsize(tmp) > 0:
                _play(tmp)
                return
            logger.warning(f"edge-tts attempt {attempt + 1}/3 failed")
        except subprocess.TimeoutExpired:
            logger.warning(f"edge-tts attempt {attempt + 1}/3 timed out")
        except Exception as e:
            logger.warning(f"edge-tts attempt {attempt + 1}/3 error: {e}")
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
        if attempt < 2:
            time.sleep(1)

    # All retries exhausted
    logger.error("edge-tts failed after 3 attempts")
    if not _is_hindi(text):
        _fallback_speak(text)

def _play(filepath: str):
    if sys.platform == "darwin":
        subprocess.run(["afplay", filepath], check=True)
    else:
        subprocess.run(["mpg123", "-q", filepath], check=True)

def _fallback_speak(text: str):
    try:
        if sys.platform == "darwin":
            subprocess.run(["say", text], check=True)
        else:
            subprocess.run(["espeak", text])
    except Exception as e:
        logger.error(f"Fallback TTS failed: {e}")
