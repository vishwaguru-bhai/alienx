# AlienX

Voice-controlled PC automation assistant for macOS/Linux.

## Features
### 🧠 System Control
- **Hardware:** Battery info, Network status, Brightness control, Volume management.
- **OS Actions:** Lock screen, Sleep, Empty Trash, Wi-Fi toggle, Calendar view.
- **Window Mgmt:** Move windows (Left/Right), System stats (CPU/RAM/Disk).

### 🖥️ Desktop & Files
- **File Ops:** Find files, Clean Downloads folder, Quick search.
- **Automation:** Open apps/URLs, Execute shell commands, Screenshot capture.

### 🤖 AI & Voice
- Push-to-talk (hotkey) & Wake word support.
- Uses OpenRouter free LLMs (Qwen/Mixtral) + Whisper for intent.
- macOS `say` TTS with Hinglish support.

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
