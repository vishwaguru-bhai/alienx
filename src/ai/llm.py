import os
import logging
from openai import OpenAI
from src.config import API_KEY, BASE_URL, MODEL
from src.ai.functions import FUNCTIONS, execute_function_call_by_name

logger = logging.getLogger(__name__)

if not API_KEY:
    logger.error("No API key found. Set OPENROUTER_API_KEY or OPENAI_API_KEY in .env")
    exit(1)

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

def process_text(text: str):
    """Send text to LLM with tool definitions."""
    try:
        tools = [{"type": "function", "function": f} for f in FUNCTIONS]
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are AlienX, a voice-controlled AI assistant. Use the provided tools to perform actions. Keep responses extremely short (1-2 words) when speaking to the user."},
                {"role": "user", "content": text}
            ],
            tools=tools,
            tool_choice="auto"
        )
        return resp.choices[0].message
    except Exception as e:
        logger.error(f"LLM error: {e}")
        return None

def process_and_speak(text: str, speak_fn):
    """Process a command string and speak the result."""
    try:
        logger.info(f"Command: {text}")
        response_msg = process_text(text)
        if not response_msg:
            speak_fn("Sorry, I couldn't process that.")
            return

        if response_msg.tool_calls:
            tool_call = response_msg.tool_calls[0]
            name = tool_call.function.name
            args = eval(tool_call.function.arguments) if tool_call.function.arguments else {}
            logger.info(f"TOOL CALL: {name} args={args}")
            result = execute_function_call_by_name(name, args)
            speak_fn(result)
        else:
            content = response_msg.content or "I'm not sure how to do that."
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
