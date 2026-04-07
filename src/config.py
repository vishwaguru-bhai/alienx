import os
from dotenv import load_dotenv

load_dotenv()

# API Configuration
API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
BASE_URL = "https://openrouter.ai/api/v1" if os.getenv("OPENROUTER_API_KEY") else None
MODEL = os.getenv("MODEL", "openrouter/auto")

# Hotkey Configuration
import sys
HOTKEY = os.getenv("HOTKEY", "<cmd>+<alt>+j" if sys.platform == 'darwin' else "<ctrl>+<alt>+j")
WAKE_WORD = os.getenv("WAKE_WORD", "").lower()
