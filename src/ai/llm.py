import os
import json
import logging
from openai import OpenAI
from src.config import API_KEY, BASE_URL, MODEL, ALIASES
from src.ai.functions import FUNCTIONS, execute_function_call_by_name

logger = logging.getLogger(__name__)

if not API_KEY:
    logger.error("No API key found. Set OPENROUTER_API_KEY or OPENAI_API_KEY in .env")
    exit(1)

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# Conversation history for multi-turn memory (last N turns)
_history = []
MAX_HISTORY = int(os.getenv("MAX_HISTORY", "6"))  # last 6 messages = 3 turns

def _apply_aliases(text: str) -> str:
    """Replace custom alias shortcut with its expanded command."""
    lower = text.lower().strip()
    for alias, expansion in ALIASES.items():
        if lower == alias.lower():
            logger.info(f"Alias matched: '{alias}' -> '{expansion}'")
            return expansion
    return text

def process_text(text: str):
    """Send text to LLM with tool definitions and conversation history."""
    global _history
    try:
        tools = [{"type": "function", "function": f} for f in FUNCTIONS]

        system_msg = {
            "role": "system",
            "content": (
                "You are AlienX, a voice-controlled AI assistant for macOS/Linux. "
                "Use ONLY the tool that directly matches the user's request. "
                "NEVER call a tool that is unrelated to what the user asked. "
                "If the user asks for time, call tell_time. If date, call tell_date. "
                "If the user asks to open an app, call open_application. "
                "If the user asks to list apps, call list_applications (no arguments). "
                "If the user asks to mute, call mute_volume (no arguments). "
                "Keep spoken responses extremely short (1-2 sentences). "
                "Respond in the same language the user speaks (Hindi/Hinglish/English)."
            )
        }

        messages = [system_msg] + _history + [{"role": "user", "content": text}]

        resp = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        msg = resp.choices[0].message

        # Update history
        _history.append({"role": "user", "content": text})
        _history.append({"role": "assistant", "content": msg.content or ""})
        if len(_history) > MAX_HISTORY * 2:
            _history = _history[-(MAX_HISTORY * 2):]

        return msg
    except Exception as e:
        logger.error(f"LLM error: {e}")
        return None

def process_and_speak(text: str, speak_fn):
    """Apply aliases, process command, speak result."""
    try:
        text = _apply_aliases(text)
        logger.info(f"Command: {text}")
        response_msg = process_text(text)
        if not response_msg:
            speak_fn("Sorry, process nahi ho saka.")
            return

        if response_msg.tool_calls:
            tool_call = response_msg.tool_calls[0]
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
            logger.info(f"TOOL CALL: {name} args={args}")
            result = execute_function_call_by_name(name, args)
            speak_fn(result)
        else:
            content = response_msg.content or "Mujhe samajh nahi aaya."
            logger.info(f"NO TOOL CALL; content: {content}")
            speak_fn(content)
    except Exception as e:
        logger.exception("Assistant error")
        speak_fn(f"Error: {e}")

def transcribe_audio_openrouter(filename):
    """Transcribe using Whisper via OpenRouter."""
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
