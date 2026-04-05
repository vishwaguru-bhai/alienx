# AlienX

Voice-controlled PC automation assistant for macOS/Linux.

## Features
- Push-to-talk (hotkey) voice commands
- Open apps, URLs
- Execute shell commands
- Get weather, time, running apps
- Lock screen, sleep
- Uses OpenRouter free LLMs (Mixtral) + Whisper
- macOS `say` TTS

## Setup

```bash
git clone git@github.com:vishwaguru-bhai/alienx.git
cd alienx
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# macOS: brew install portaudio
cp .env.example .env
# Edit .env: add OPENROUTER_API_KEY
python -m src.main
```

Press `Cmd+Option+J` (Mac) or `Ctrl+Alt+J` (Linux) to activate.

## License
MIT
