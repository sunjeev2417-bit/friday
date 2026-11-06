import json
import re
import os
import tempfile
from pathlib import Path
from datetime import datetime

from friday_config import MEMORY_FILE, NOTES_FILE


# ============================================================
# FRIDAY SMART MEMORY
# ============================================================

MEMORY_FILE = Path(MEMORY_FILE)
NOTES_FILE = Path(NOTES_FILE)

HISTORY_FILE = MEMORY_FILE.parent / "conversation_history.jsonl"


# ------------------------------------------------------------
# TEXT NORMALIZATION
# ------------------------------------------------------------

def _normalize(text):
    """Normalize text for matching and searching."""
    text = str(text).lower().strip()

    # Treat common American and British spellings consistently.
    text = re.sub(r"\bcolou?r\b", "color", text)
    text = re.sub(r"\bfavou?rite\b", "favorite", text)
    text = re.sub(r"\borganise\b", "organize", text)
    text = re.sub(r"\brecognise\b", "recognize", text)

    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return " ".join(text.split())


def _canonical_key(key):
    """Convert equivalent memory keys into one standard key."""
    key = _normalize(key)

    # Remove conversational prefixes.
    prefixes = (
        "please remember ",
        "remember that ",
        "remember ",
        "my ",
        "about me ",
    )

    changed = True
    while changed:
        changed = False

        for prefix in prefixes:
            if key.startswith(prefix):
                key = key[len(prefix):].strip()
                changed = True

    # Normalize common equivalent labels.
    aliases = {
        "favorite colour": "favorite color",
        "favourite color": "favorite color",
        "favourite colour": "favorite color",
        "my favorite color": "favorite color",
        "my favourite colour": "favorite color",
        "favorite foods": "favorite food",
        "favourite food": "favorite food",
        "favorite movies": "favorite movie",
        "favourite movie": "favorite movie",
        "favorite songs": "favorite song",
        "favourite song": "favorite song",
    }

    return aliases.get(key, key)


# ------------------------------------------------------------
# SAFE JSON FILE OPERATIONS
# ------------------------------------------------------------

def _load(path, default):
    try:
        if not path.exists():
            return default

        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)

    except (OSError, json.JSONDecodeError):
        return default


def _save(path, data):
    """Write JSON safely using a temporary file."""
    path.parent.mkdir(parents=True, exist_ok=True)

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(path.parent),
            suffix=".tmp",
            delete=False,
        ) as file:
            json.dump(
                data,
                file,
                indent=2,
                ensure_ascii=False,
            )
            file.flush()
            os.fsync(file.fileno())
            temp_path = Path(file.name)

        os.replace(temp_path, path)

    finally:
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


# ------------------------------------------------------------
# MEMORY MIGRATION AND DUPLICATE CLEANUP
# ------------------------------------------------------------

def _load_memory():
    """Load memories and merge duplicate keys."""
    raw = _load(MEMORY_FILE, {})

    if not isinstance(raw, dict):
        return {}

    cleaned = {}

    for original_key, item in raw.items():
        key = _canonical_key(original_key)

        if not key:
            continue

        if isinstance(item, dict):
            value = item.get("value", "")
            category = item.get("category", "GENERAL")
            updated = item.get("updated", "")
        else:
            value = item
            category = "GENERAL"
            updated = ""

        # Prefer the existing canonical entry if duplicates exist.
        # Otherwise, retain the first valid entry encountered.
        if key not in cleaned:
            cleaned[key] = {
                "value": value,
                "category": category,
                "updated": updated,
            }

        # If duplicate entries disagree, retain the most recently
        # updated entry when timestamps are available.
        elif updated and updated > cleaned[key].get("updated", ""):
            cleaned[key] = {
                "value": value,
                "category": category,
                "updated": updated,
            }

    # Persist the cleaned version so duplicates stay removed.
    if cleaned != raw:
        _save(MEMORY_FILE, cleaned)

    return cleaned


# ------------------------------------------------------------
# REMEMBER
# ------------------------------------------------------------

def remember(key, value, category="GENERAL"):
    """Save a fact or update an existing fact."""
    key = _canonical_key(key)
    value = str(value).strip()

    if not key or not value:
        return "I need a memory name and value, boss."

    data = _load_memory()

    data[key] = {
        "value": value,
        "category": str(category).upper(),
        "updated": datetime.now().isoformat(timespec="seconds"),
    }

    _save(MEMORY_FILE, data)

    return f"I've updated my memory about {key}, boss."


# ------------------------------------------------------------
# RECALL
# ------------------------------------------------------------

def recall(key=None):
    """Recall one fact or list all stored facts."""
    data = _load_memory()

    if key:
        key = _canonical_key(key)

        if key in data:
            return str(data[key].get("value", ""))

        # Try matching equivalent key phrases.
        matches = [
            (stored_key, item)
            for stored_key, item in data.items()
            if key in stored_key or stored_key in key
        ]

        if len(matches) == 1:
            return str(matches[0][1].get("value", ""))

        return f"I don't have anything stored for {key}, boss."

    if not data:
        return "My memory is currently empty, boss."

    lines = ["Here is what I remember, boss:"]

    for key, item in data.items():
        value = item.get("value", "")
        category = item.get("category", "GENERAL")

        lines.append(f"- {key}: {value} [{category}]")

    return "\n".join(lines)


# ------------------------------------------------------------
# FORGET
# ------------------------------------------------------------

def forget(key):
    """Remove a stored fact."""
    key = _canonical_key(key)
    data = _load_memory()

    if key in data:
        del data[key]
        _save(MEMORY_FILE, data)

        return f"I've removed {key} from my memory, boss."

    return f"I couldn't find {key} in my memory, boss."


# ------------------------------------------------------------
# NOTES
# ------------------------------------------------------------

def add_note(text):
    notes = _load(NOTES_FILE, [])

    if not isinstance(notes, list):
        notes = []

    notes.append({
        "text": str(text).strip(),
        "created": datetime.now().isoformat(timespec="seconds"),
    })

    _save(NOTES_FILE, notes)

    return "Note saved, boss."


def list_notes():
    notes = _load(NOTES_FILE, [])

    if not notes:
        return "You don't have any saved notes, boss."

    return "\n".join(
        f"{i + 1}. {note.get('text', '')}"
        for i, note in enumerate(notes)
    )


def search_notes(query, limit=10):
    notes = _load(NOTES_FILE, [])
    query = _normalize(query)

    if not isinstance(notes, list):
        return "I couldn't read your saved notes, boss."

    matches = [
        note for note in notes
        if query in _normalize(note.get("text", ""))
    ]

    if not matches:
        return f"I couldn't find any matching notes, boss."

    return "\n".join(
        f"- {note.get('text', '')}"
        for note in matches[:limit]
    )


# ------------------------------------------------------------
# CONVERSATION HISTORY
# ------------------------------------------------------------

def remember_turn(user_text, assistant_text):
    """Archive each user-assistant exchange."""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "user": str(user_text),
        "assistant": str(assistant_text),
    }

    with open(HISTORY_FILE, "a", encoding="utf-8") as file:
        file.write(json.dumps(entry, ensure_ascii=False) + "\n")


def search_history(query, limit=15):
    """Search previous conversations."""
    query = _normalize(query)

    if not HISTORY_FILE.exists():
        return "I don't have any conversation history yet, boss."

    matches = []

    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as file:
            for line in file:
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                user_text = entry.get("user", "")
                assistant_text = entry.get("assistant", "")
                combined = _normalize(user_text + " " + assistant_text)

                if query and query in combined:
                    matches.append(entry)

    except OSError:
        return "I couldn't access conversation history, boss."

    if not matches:
        return "I couldn't find a matching conversation, boss."

    results = []

    for entry in matches[-limit:]:
        results.append(
            f"You: {entry.get('user', '')}\n"
            f"Friday: {entry.get('assistant', '')}"
        )

    return "\n\n".join(results)


# ------------------------------------------------------------
# AUTOMATIC FACT DETECTION
# ------------------------------------------------------------

def auto_save_memory(user_text):
    """
    Automatically save a limited set of clearly stated personal facts.
    Ambiguous statements are not automatically stored.
    """
    text = str(user_text).strip()

    patterns = [
        (
            r"^(?:my )?(?:favorite|favourite) colou?r is (.+)$",
            "favorite color",
        ),
        (
            r"^(?:my )?(?:favorite|favourite) food is (.+)$",
            "favorite food",
        ),
        (
            r"^(?:my )?(?:favorite|favourite) movie is (.+)$",
            "favorite movie",
        ),
        (
            r"^(?:my )?(?:favorite|favourite) song is (.+)$",
            "favorite song",
        ),
        (
            r"^i am learning (.+)$",
            "currently learning",
        ),
        (
            r"^i work as (.+)$",
            "occupation",
        ),
        (
            r"^my birthday is (.+)$",
            "birthday",
        ),
    ]

    normalized_text = _normalize(text)

    for pattern, key in patterns:
        match = re.match(pattern, normalized_text)

        if match:
            value = match.group(1).strip()

            if value:
                remember(key, value, "PERSONAL")
                return True

    return False


# ------------------------------------------------------------
# MEMORY CONTEXT FOR FRIDAY'S AI
# ------------------------------------------------------------

def get_memory_context(max_chars=2500):
    """Provide stored facts to Friday's local AI model."""
    data = _load_memory()

    if not data:
        return ""

    lines = []

    for key, item in data.items():
        value = item.get("value", "")
        lines.append(f"{key}: {value}")

    context = "\n".join(lines)

    return context[:max_chars]


# ------------------------------------------------------------
# SELF-TEST
# ------------------------------------------------------------

if __name__ == "__main__":
    print("Friday smart memory: ONLINE")
    print(remember("favorite colour", "orange", "PERSONAL"))
    print("American spelling:", recall("favorite color"))
    print("British spelling:", recall("favourite colour"))
    print("\nAll memories:")
    print(recall())