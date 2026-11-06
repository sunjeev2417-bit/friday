from pathlib import Path
from urllib.parse import urlparse
from math import isfinite

# Friday project
PROJECT_DIR = Path(__file__).resolve().parent

# Ollama
OLLAMA_URL = "http://localhost:11434/api/chat"
LLM_MODEL = "qwen3:1.7b"

# Friday personality
ASSISTANT_NAME = "Friday"
USER_TITLE = "boss"

# Voice
VOICE_RATE = 175
VOICE_VOLUME = 1.0

# Storage
DATA_DIR = PROJECT_DIR / "friday_data"
MEMORY_FILE = DATA_DIR / "memory.json"
NOTES_FILE = DATA_DIR / "notes.json"
LOG_FILE = DATA_DIR / "friday.log"


def validate_config():
    """Validate Friday's configuration without changing its settings."""

    if not isinstance(OLLAMA_URL, str):
        raise ValueError("OLLAMA_URL must be a string")

    try:
        parsed_url = urlparse(OLLAMA_URL)
        valid_url = (
            parsed_url.scheme in ("http", "https")
            and bool(parsed_url.hostname)
        )
    except (ValueError, TypeError):
        valid_url = False

    if not valid_url:
        raise ValueError(
            "OLLAMA_URL must have an http/https scheme and hostname"
        )

    for name, value in (
        ("LLM_MODEL", LLM_MODEL),
        ("ASSISTANT_NAME", ASSISTANT_NAME),
        ("USER_TITLE", USER_TITLE),
    ):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a nonempty string")

    if (
        isinstance(VOICE_RATE, bool)
        or not isinstance(VOICE_RATE, int)
        or VOICE_RATE <= 0
    ):
        raise ValueError("VOICE_RATE must be a positive integer")

    if (
        isinstance(VOICE_VOLUME, bool)
        or not isinstance(VOICE_VOLUME, (int, float))
        or not isfinite(VOICE_VOLUME)
        or not 0.0 <= VOICE_VOLUME <= 1.0
    ):
        raise ValueError(
            "VOICE_VOLUME must be a finite number between 0.0 and 1.0"
        )

    for name, value in (
        ("PROJECT_DIR", PROJECT_DIR),
        ("DATA_DIR", DATA_DIR),
        ("MEMORY_FILE", MEMORY_FILE),
        ("NOTES_FILE", NOTES_FILE),
        ("LOG_FILE", LOG_FILE),
    ):
        if not isinstance(value, Path):
            raise ValueError(f"{name} must be a Path instance")

    return True



# Preserve original behavior: create the storage directory.
DATA_DIR.mkdir(exist_ok=True)
