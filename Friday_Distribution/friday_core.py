import re
import requests
from pathlib import Path

from friday_config import OLLAMA_URL, LLM_MODEL

from friday_tools import (
    open_app,
    open_website,
    web_search,
    open_folder,
    open_special_folder,
    get_cpu_usage,
    get_memory_usage,
    get_battery_status,
    get_system_info,
    get_storage_usage,
    get_pc_status,
    get_pc_health,
    set_volume_up,
    set_volume_down,
    toggle_mute,
    lock_pc,
    sleep_pc,
    restart_pc,
    shutdown_pc,
    cancel_shutdown,
    get_detailed_system_info,
)

from friday_memory import (
    remember,
    recall,
    forget,
    add_note,
    list_notes,
    remember_turn,
    auto_save_memory,
    search_history,
    search_notes,
    get_memory_context,
)


# =========================================================
# FRIDAY AI CORE
# =========================================================

SYSTEM_PROMPT = """
You are Friday, a personal AI assistant.

Personality:
- Calm, intelligent, concise and helpful.
- Slightly futuristic and confident.
- Address the user as boss.
- Never call yourself Qwen.
- Keep spoken responses reasonably short.

You are the reasoning core of a local Windows AI assistant.

IMPORTANT:
If the user asks about CPU, RAM, storage, battery, or PC status,
use the available local system tools whenever possible.

Use saved memory to personalize responses when relevant.
Do not invent personal facts that are not in memory.
"""


# =========================================================
# AI
# =========================================================

def ask_ai(user_message):
    memory_context = ""

    try:
        memory_context = get_memory_context()
    except Exception:
        memory_context = ""

    system_message = SYSTEM_PROMPT

    if memory_context:
        system_message += (
            "\n\nSaved facts about the user:\n"
            + memory_context
            + "\nUse these facts only when relevant."
        )

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {
                "role": "system",
                "content": system_message,
            },
            {
                "role": "user",
                "content": user_message,
            },
        ],
        "stream": False,
        "think": False,
        "options": {
            "temperature": 0.6,
        },
    }

    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=120,
        )

        response.raise_for_status()

        data = response.json()

        return data["message"]["content"].strip()

    except requests.exceptions.ConnectionError:
        return (
            "My local reasoning core is offline. "
            "Please make sure Ollama is running."
        )

    except requests.exceptions.Timeout:
        return "The local reasoning core took too long to respond."

    except Exception as error:
        return f"I encountered an error: {error}"


# =========================================================
# NATURAL COMMAND ALIASES
# =========================================================

NATURAL_COMMAND_ALIASES = {
    "how's my pc": "pc status",
    "hows my pc": "pc status",
    "how's my computer": "pc status",
    "hows my computer": "pc status",

    "what's going on with my pc": "pc status",
    "whats going on with my pc": "pc status",
    "what's going on with my computer": "pc status",
    "whats going on with my computer": "pc status",

    "what's happening with my pc": "pc status",
    "whats happening with my pc": "pc status",

    "how is my system": "pc status",
    "how's my system": "pc status",
    "hows my system": "pc status",

    "is everything okay with my pc": "pc health",
    "is everything okay with my computer": "pc health",

    "is my pc running fine": "pc health",
    "is my computer running fine": "pc health",

    "is my pc running normally": "pc health",
    "is my computer running normally": "pc health",

    "is my pc under load": "pc health",
    "is my computer under load": "pc health",
}


# =========================================================
# COMMAND NORMALIZATION
# =========================================================

def normalize_command(text):
    """Normalize spelling variations and natural commands."""

    normalized = " ".join(text.lower().strip().split())

    normalized = normalized.replace("colour", "color")
    normalized = normalized.replace("favourite", "favorite")

    typo_corrections = {
        "coloue": "color",
        "colur": "color",
        "colro": "color",
        "favo rite": "favorite",
        "favourit": "favorite",
        "favrite": "favorite",
        "favou rite": "favorite",
    }

    words = normalized.split()

    normalized = " ".join(
        typo_corrections.get(word, word)
        for word in words
    )

    return NATURAL_COMMAND_ALIASES.get(
        normalized,
        normalized,
    )


def extract_argument(original, prefix):
    """Safely extract argument preserving original casing and punctuation."""
    words = prefix.strip().split()
    if not words:
        return original.strip()
    pattern = r"^\s*" + r"\s+".join(re.escape(w) for w in words) + r"\s*(.*)$"
    match = re.match(pattern, original, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


# =========================================================
# COMMAND ROUTER
# =========================================================

def handle_command(command):

    original = command.strip()
    text = normalize_command(original)

    if not text:
        return ""

    # =====================================================
    # OPEN APPLICATIONS
    # =====================================================

    apps = [
        "calculator",
        "notepad",
        "paint",
        "explorer",
        "settings",
        "chrome",
        "edge",
    ]

    for app in apps:
        if text in (
            f"open {app}",
            f"launch {app}",
            f"start {app}",
        ):
            return open_app(app)

    # =====================================================
    # PC HEALTH
    # =====================================================

    pc_health_commands = [
        "is my pc healthy",
        "is my computer healthy",
        "check my pc health",
        "check my computer health",
        "check pc health",
        "check computer health",
        "pc health",
        "computer health",
        "system health",
        "is my pc okay",
        "is my computer okay",
        "tell me if my pc is healthy",
        "is my pc running fine",
        "is my computer running fine",
        "is my pc running normally",
        "is my computer running normally",
        "is my pc under load",
        "is my computer under load",
    ]

    if text in pc_health_commands:
        return get_pc_health()

    # =====================================================
    # PC STATUS
    # =====================================================

    pc_status_commands = [
        "check my pc",
        "check pc",
        "check my computer",
        "check computer",
        "pc status",
        "computer status",
        "system status",
        "check my system",
        "how is my system doing",
        "how is my computer doing",
        "how is my pc doing",
        "how is my computer",
        "how is my pc",
        "how is my computer running",
        "how is my pc running",
        "how is my computer working",
        "how is my pc working",
        "give me a pc status",
        "give me pc status",
        "give me system status",
        "check the computer",
        "check the pc",
        "tell me about my pc",
        "tell me about my computer",
        "tell me how my pc is doing",
        "tell me how my computer is doing",
    ]

    if (
        text in pc_status_commands
        or "check my pc" in text
        or "check my computer" in text
        or "pc status" in text
        or "computer status" in text
        or "system status" in text
        or "how is my pc" in text
        or "how is my computer" in text
        or "how is my pc doing" in text
        or "how is my computer doing" in text
        or "how is my pc running" in text
        or "how is my computer running" in text
    ):
        return get_pc_status()

    # =====================================================
    # CPU + RAM COMBINED
    # =====================================================

    cpu_words = [
        "cpu",
        "processor",
    ]

    ram_words = [
        "ram",
        "memory",
    ]

    asks_cpu = any(word in text for word in cpu_words)
    asks_ram = any(word in text for word in ram_words)

    usage_words = [
        "usage",
        "using",
        "used",
        "utilization",
        "load",
        "currently",
        "how much",
        "how many",
        "percentage",
        "percent",
    ]

    asks_usage = any(word in text for word in usage_words)

    if asks_cpu and asks_ram and asks_usage:
        cpu_result = get_cpu_usage()
        ram_result = get_memory_usage()

        return f"{cpu_result} {ram_result}"

    # =====================================================
    # CPU
    # =====================================================

    cpu_keywords = [
        "cpu usage",
        "cpu utilization",
        "cpu load",
        "cpu percentage",
        "cpu percent",
        "how much cpu",
        "how much of my cpu",
        "cpu am i using",
        "how much processor",
        "processor usage",
        "processor utilization",
        "processor load",
        "processor percentage",
        "check my cpu",
        "check cpu",
        "my cpu usage",
        "what is my cpu",
        "what's my cpu",
        "how is my cpu",
        "how is my processor",
        "what is my cpu usage",
        "what is my processor usage",
        "how busy is my cpu",
        "how busy is my processor",
    ]

    if any(keyword in text for keyword in cpu_keywords):
        return get_cpu_usage()

    # =====================================================
    # RAM / MEMORY USAGE
    # =====================================================

    ram_keywords = [
        "ram usage",
        "ram utilization",
        "ram percentage",
        "ram percent",
        "memory usage",
        "memory utilization",
        "memory percentage",
        "memory percent",
        "how much ram",
        "how much memory",
        "how much of my ram",
        "how much of my memory",
        "ram am i using",
        "memory am i using",
        "ram being used",
        "memory being used",
        "ram currently used",
        "memory currently used",
        "check my ram",
        "check ram",
        "what is my ram",
        "what's my ram",
        "how is my ram",
        "what is my ram usage",
        "what is my memory usage",
        "how much ram am i using right now",
        "how much memory am i using right now",
        "how full is my ram",
        "how full is my memory",
        "system memory",
        "system memory usage",
        "check system memory",
        "what is my system memory",
    ]

    if any(keyword in text for keyword in ram_keywords):
        return get_memory_usage()

    # =====================================================
    # BATTERY
    # =====================================================

    battery_keywords = [
        "battery",
        "battery status",
        "battery level",
        "battery percentage",
        "battery percent",
        "how much battery",
        "how much charge",
        "charge level",
        "check my battery",
        "check battery",
        "what is my battery",
        "what's my battery",
        "how is my battery",
        "how much battery do i have",
        "how much charge do i have",
        "how much battery is left",
        "how much battery remains",
        "is my battery low",
        "is my laptop battery low",
    ]

    if any(keyword in text for keyword in battery_keywords):
        return get_battery_status()

    # =====================================================
    # SYSTEM INFORMATION
    # =====================================================

    system_keywords = [
        "system information",
        "system info",
        "pc information",
        "pc info",
        "computer information",
        "computer info",
        "system specifications",
        "system specs",
        "pc specifications",
        "pc specs",
        "computer specifications",
        "computer specs",
        "my system",
        "my pc specs",
        "my computer specs",
        "what are my pc specs",
        "what are my computer specs",
    ]

    if any(keyword in text for keyword in system_keywords):
        return get_system_info()

    # =====================================================
    # STORAGE
    # =====================================================

    storage_keywords = [
        "storage usage",
        "disk usage",
        "disk space",
        "storage",
        "how much storage am i using",
        "how much disk am i using",
        "how much disk space am i using",
        "how much space am i using",
        "how much storage am i using right now",
        "how much space do i have left",
        "how much disk space do i have left",
        "is my storage full",
        "is my disk full",
        "is my storage getting full",
    ]

    if any(keyword in text for keyword in storage_keywords):
        return get_storage_usage()

    # =====================================================
    # PROJECT / CUSTOM FOLDERS
    # =====================================================

    friday_root = Path(__file__).resolve().parent

    custom_folders = {
        "friday folder": friday_root,
        "friday": friday_root,
        "jarvis folder": friday_root,
        "jarvis": friday_root,
        "project folder": friday_root,
        "project": friday_root,
    }

    for folder_name, folder_path in custom_folders.items():
        if text in (
            f"open {folder_name}",
            f"open my {folder_name}",
            f"show {folder_name}",
            f"show my {folder_name}",
        ):
            return open_folder(str(folder_path))

    # =====================================================
    # SPECIAL WINDOWS FOLDERS
    # =====================================================

    special_folders = [
        "desktop",
        "downloads",
        "documents",
        "pictures",
        "music",
        "videos",
    ]

    for folder in special_folders:
        if text in (
            f"open {folder}",
            f"open my {folder}",
            f"show {folder}",
            f"show my {folder}",
        ):
            return open_special_folder(folder)

    # =====================================================
    # WEBSITES
    # =====================================================

    websites = {
        "youtube": "https://www.youtube.com",
        "google": "https://www.google.com",
        "gmail": "https://mail.google.com",
        "github": "https://github.com",
    }

    for name, url in websites.items():
        if text in (
            f"open {name}",
            f"launch {name}",
            f"start {name}",
        ):
            return open_website(url)

    # =====================================================
    # WEB SEARCH
    # =====================================================

    search_prefixes = [
        "search the web for ",
        "search for ",
        "google ",
        "look up ",
        "find information about ",
    ]

    for prefix in search_prefixes:
        if text.startswith(prefix):
            query = extract_argument(original, prefix)

            if query:
                return web_search(query)

    # =====================================================
    # MEMORY
    # =====================================================

    # Explicitly stated favorite color.
    if text.startswith("my favorite color is "):
        parts = re.split(r"\s+is\s+", original, maxsplit=1, flags=re.IGNORECASE)
        value = parts[-1].strip() if len(parts) > 1 else ""

        if value:
            return remember(
                "favorite color",
                value,
                "PERSONAL",
            )

    # Explicit remember command.
    if text == "remember" or text.startswith("remember "):
        content = extract_argument(original, "remember")

        if not content:
            return "Tell me what you want me to remember, boss."

        parts = re.split(r"\s+is\s+", content, maxsplit=1, flags=re.IGNORECASE)

        if len(parts) == 2:
            key = parts[0].strip()
            value = parts[1].strip()

            if key and value:
                return remember(key, value, "GENERAL")

        return remember(
            content,
            "User asked Friday to remember this.",
            "GENERAL",
        )

    # Recall one fact.
    if text == "recall" or text.startswith("recall "):
        key = extract_argument(original, "recall")

        if key:
            return recall(key)

        return "Tell me what you want me to recall, boss."

    # List all memories.
    show_memory_commands = {
        "what do you remember",
        "what do you remember about me",
        "show my memory",
        "show me my memory",
        "what did i ask you to remember",
        "what did i tell you to remember",
        "what have i asked you to remember",
        "what have you remembered",
        "list my memories",
        "show all memories",
        "what is in my memory",
        "what's in my memory",
        "what do you have in memory",
        "check my memory",
        "check memory",
    }

    if text in show_memory_commands:
        return recall()

    # Search the conversation archive.
    history_prefixes = [
        "search conversation history for ",
        "search my conversations for ",
        "search my history for ",
        "what did we discuss about ",
        "what did we talk about ",
        "what did i say about ",
        "what did i tell you about ",
    ]

    for prefix in history_prefixes:
        if text.startswith(prefix):
            query = extract_argument(original, prefix)

            if query:
                return search_history(query)

            return "Tell me what you want to search for, boss."

    # Search saved notes.
    if text in ("search my notes", "search my notes for") or text.startswith("search my notes for "):
        query = extract_argument(original, "search my notes for")

        if query:
            return search_notes(query)

        return "Tell me what note to search for, boss."

    # Forget a saved fact.
    if text == "forget" or text.startswith("forget "):
        key = extract_argument(original, "forget")

        if key:
            return forget(key)

        return "Tell me which memory to forget, boss."

    # =====================================================
    # NOTES
    # =====================================================

    note_prefixes = [
        "take a note ",
        "save a note ",
        "note ",
    ]

    if text in ("take a note", "save a note"):
        return "Tell me what note to save, boss."

    for prefix in note_prefixes:
        if text.startswith(prefix):
            note = extract_argument(original, prefix)

            if note:
                return add_note(note)

            return "Tell me what note to save, boss."

    if text in (
        "show my notes",
        "list my notes",
        "read my notes",
    ):
        return list_notes()

    # =====================================================
    # DIRECT WEBSITE
    # =====================================================

    if text == "open website" or text.startswith("open website "):
        url = extract_argument(original, "open website")

        if url:
            return open_website(url)

        return "Tell me which website to open, boss."

    # =====================================================
    # VOLUME UP
    # =====================================================

    if (
        text in [
            "increase volume",
            "increase the volume",
            "turn up volume",
            "turn up the volume",
            "volume up",
            "make it louder",
            "make the volume louder",
            "louder",
            "raise the volume",
            "raise volume",
        ]
        or "increase volume" in text
        or "increase the volume" in text
        or "turn up the volume" in text
        or "make the volume louder" in text
        or "raise the volume" in text
    ):
        return set_volume_up()

    # =====================================================
    # VOLUME DOWN
    # =====================================================

    if (
        text in [
            "decrease volume",
            "decrease the volume",
            "turn down volume",
            "turn down the volume",
            "volume down",
            "make it quieter",
            "make the volume quieter",
            "quieter",
            "lower the volume",
            "lower volume",
        ]
        or "decrease volume" in text
        or "decrease the volume" in text
        or "turn down the volume" in text
        or "make the volume quieter" in text
        or "lower the volume" in text
    ):
        return set_volume_down()

    # =====================================================
    # MUTE / UNMUTE
    # =====================================================

    if (
        text in [
            "mute",
            "mute volume",
            "mute my pc",
            "mute the pc",
            "mute my computer",
            "mute the computer",
            "unmute",
            "unmute volume",
            "unmute my pc",
            "unmute the pc",
            "unmute my computer",
            "unmute the computer",
            "toggle mute",
            "toggle mute volume",
            "toggle the mute",
        ]
        or "mute my pc" in text
        or "mute the pc" in text
        or "unmute my pc" in text
        or "unmute the pc" in text
        or "toggle mute" in text
    ):
        return toggle_mute()

    # =====================================================
    # LOCK PC
    # =====================================================

    if text in [
        "lock my pc",
        "lock pc",
        "lock my computer",
        "lock computer",
    ]:
        return lock_pc()

    # =====================================================
    # SLEEP PC
    # =====================================================

    if text in [
        "sleep",
        "put my pc to sleep",
        "put pc to sleep",
        "sleep my pc",
    ]:
        return sleep_pc()

    # =====================================================
    # RESTART PC
    # =====================================================

    if text in [
        "restart",
        "restart my pc",
        "restart pc",
        "restart my computer",
        "restart computer",
    ]:
        return restart_pc()

    # =====================================================
    # SHUTDOWN PC
    # =====================================================

    if text in [
        "shutdown",
        "shut down",
        "shutdown my pc",
        "shutdown pc",
        "shut down my pc",
        "shut down pc",
        "shutdown my computer",
        "shut down my computer",
    ]:
        return shutdown_pc()

    # =====================================================
    # CANCEL SHUTDOWN / RESTART
    # =====================================================

    if text in [
        "cancel shutdown",
        "cancel restart",
        "stop shutdown",
        "stop restart",
    ]:
        return cancel_shutdown()

    # =====================================================
    # DETAILED SYSTEM INFORMATION
    # =====================================================

    if text in [
        "detailed system information",
        "detailed system info",
        "detailed pc information",
        "detailed pc info",
        "full system information",
        "full pc information",
        "show detailed specs",
        "show detailed system specs",
    ]:
        return get_detailed_system_info()

    # =====================================================
    # AI FALLBACK
    # =====================================================

    return ask_ai(original)


# =========================================================
# MAIN
# =========================================================

def main():

    print("=" * 55)
    print("FRIDAY AI CORE + TOOLS")
    print("=" * 55)

    print("Model:", LLM_MODEL)
    print("Tools: ONLINE")
    print("Memory: ONLINE")
    print("Type 'exit' to stop.")
    print()

    while True:
        try:
            user_input = input("Boss: ").strip()

        except (KeyboardInterrupt, EOFError):
            print("\nFriday: Goodbye, boss.")
            break

        if user_input.lower() in {"exit", "quit"}:
            print("Friday: Goodbye, boss.")
            break

        if not user_input:
            continue

        try:
            response = handle_command(user_input)

        except Exception as error:
            response = f"I encountered an error: {error}"

        # Archive every conversation turn.
        try:
            remember_turn(user_input, response)
        except Exception as error:
            print(f"[Memory archive warning] {error}")

        # Save explicitly stated personal facts.
        try:
            auto_save_memory(user_input)
        except Exception as error:
            print(f"[Memory saving warning] {error}")

        print("Friday:", response)
        print()


if __name__ == "__main__":
    main()