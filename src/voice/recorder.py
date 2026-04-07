import sounddevice as sd
import numpy as np
import wave
import tempfile
import os
import logging
import speech_recognition as sr
from src.ai.llm import transcribe_audio_openrouter

logger = logging.getLogger(__name__)

def record_audio(duration=None, fs=16000):
    """Record audio from microphone."""
    if duration is None:
        duration = int(os.getenv("RECORD_DURATION", "3"))
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

def transcribe_audio(filename):
    """Transcribe using Google SR with fallback to OpenRouter."""
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

def listen(duration=None):
    """Record and return transcribed text."""
    if duration is None:
        duration = int(os.getenv("RECORD_DURATION", "3"))
    audio, fs = record_audio(duration)
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        tmp_name = tmp.name
    try:
        save_wav(audio, fs, tmp_name)
        text = transcribe_audio(tmp_name)
        logger.info(f"Heard: {text}")
        return text
    finally:
        os.unlink(tmp_name)
