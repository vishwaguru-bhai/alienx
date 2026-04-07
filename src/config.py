import os
import sys
from dotenv import load_dotenv

load_dotenv()

# API Configuration
API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
BASE_URL = "https://openrouter.ai/api/v1" if os.getenv("OPENROUTER_API_KEY") else None
MODEL = os.getenv("MODEL", "openrouter/auto")

# Hotkey Configuration
HOTKEY = os.getenv("HOTKEY", "<cmd>+<alt>+j" if sys.platform == 'darwin' else "<ctrl>+<alt>+j")
WAKE_WORD = os.getenv("WAKE_WORD", "").lower()

# Custom Aliases — loaded from ALIASES env var as JSON
# Example in .env: ALIASES={"boss mode": "do not disturb on", "kaam shuru": "open VS Code"}
def _load_aliases() -> dict:
    raw = os.getenv("ALIASES", "")
    if not raw:
        return {}
    try:
        data = __import__('json').loads(raw)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}

ALIASES = _load_aliases()
