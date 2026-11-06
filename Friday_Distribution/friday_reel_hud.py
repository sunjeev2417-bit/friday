import sys
import os
import json
import math
import time
import random
import threading
import subprocess
import webbrowser
import platform
import socket
import re
from datetime import datetime
from pathlib import Path

import requests
import psutil
import cv2
import mediapipe as mp
import pyttsx3

import os
import tempfile
import wave
import winsound

try:
    from piper import PiperVoice, SynthesisConfig
except ImportError:
    PiperVoice = None
    SynthesisConfig = None

import speech_recognition as sr

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import (
    QPainter,
    QPen,
    QBrush,
    QColor,
    QFont,
    QSurfaceFormat,
)
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtWidgets import QApplication, QLineEdit, QPushButton

from OpenGL.GL import (
    glBegin,
    glEnd,
    glVertex3f,
    glVertex2f,
    glColor4f,
    glPointSize,
    glLineWidth,
    glClear,
    glClearColor,
    glEnable,
    glDisable,
    glBlendFunc,
    glDepthFunc,
    glMatrixMode,
    glLoadIdentity,
    glRotatef,
    glTranslatef,
    glPushMatrix,
    glPopMatrix,
    glFlush,
    glViewport,
    glOrtho,
    glHint,
    GL_POINTS,
    GL_COLOR_BUFFER_BIT,
    GL_DEPTH_BUFFER_BIT,
    GL_DEPTH_TEST,
    GL_BLEND,
    GL_SRC_ALPHA,
    GL_ONE_MINUS_SRC_ALPHA,
    GL_ONE,
    GL_PROJECTION,
    GL_MODELVIEW,
    GL_LINE_LOOP,
    GL_LINES,
    GL_LINE_STRIP,
    GL_TRIANGLE_FAN,
    GL_LINE_SMOOTH,
    GL_LINE_SMOOTH_HINT,
    GL_NICEST,
    GL_POINT_SMOOTH,
)

from OpenGL.GLU import gluPerspective


class FridayReelHUD(QOpenGLWidget):

    # =========================================================
    # FRIDAY CORE
    # =========================================================

    LLM_URL = "http://localhost:11434/api/chat"
    LLM_MODEL = "qwen3:1.7b"

    FRIDAY_DIR = Path.home() / ".friday"

    MEMORY_FILE = FRIDAY_DIR / "memory.json"
    NOTES_FILE = FRIDAY_DIR / "notes.json"
    TRANSCRIPT_FILE = FRIDAY_DIR / "transcript.log"

    def __init__(self):
        super().__init__()

        # -----------------------------------------------------
        # WINDOW
        # -----------------------------------------------------

        self.setWindowTitle(
            "F.R.I.D.A.Y. â€” Cinematic Hand Interface"
        )

        self.setMinimumSize(1100, 700)
        self.setMouseTracking(True)

        self.close_button = QPushButton("X", self)
        self.close_button.setFixedSize(58, 42)
        self.close_button.setStyleSheet(
            "QPushButton { background-color: #000000; color: #ffffff; "
            "border: 1px solid #ffffff; border-radius: 4px; "
            "font-size: 25px; font-weight: bold; } "
            "QPushButton:hover { background-color: #ffffff; color: #000000; }"
        )
        self.close_button.clicked.connect(self.close)
        self.close_button.move(0, 0)
        self.close_button.raise_()
        self.close_button.show()

        # -----------------------------------------------------
        # FRIDAY DIRECTORY
        # -----------------------------------------------------

        self.FRIDAY_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        # -----------------------------------------------------
        # STATE
        # -----------------------------------------------------

        self.voice_running = True
        self.camera_running = True

        self.voice_ready = False
        self.voice_busy = False

        self.camera_online = False
        self.hand_online = False
        self.hand_visible = False

        self.pending_action = None

        self.mouse_x = 0.5
        self.mouse_y = 0.5

        self.hand_x = 0.5
        self.hand_y = 0.5

        self.gesture = "NONE"
        self.last_gesture = "NONE"

        self.gesture_time = 0.0
        self.last_action_time = 0.0

        self.start_time = time.perf_counter()

        # -----------------------------------------------------
        # LOCKS
        # -----------------------------------------------------

        self.voice_lock = threading.RLock()
        self.ai_lock = threading.Lock()

        # -----------------------------------------------------
        # AI CONVERSATION
        # -----------------------------------------------------

        self.conversation_history = []

        # -----------------------------------------------------
        # MEMORY
        # -----------------------------------------------------

        self.memory_data = {
            "preferences": {},
            "personal": {},
            "education": {},
            "work": {},
            "goals": {},
            "hobbies": {},
            "computer": {},
            "general": {},
        }

        self.notes = []

        self.load_memory()
        self.load_notes()

        # -----------------------------------------------------
        # VOICE
        # -----------------------------------------------------

        self.voice_engine = None
        self.zira_voice = None

        # -----------------------------------------------------
        # COMMAND BOX
        # -----------------------------------------------------

        self.command_input = QLineEdit(self)

        self.command_input.setPlaceholderText(
            "Type a command for Friday..."
        )

        self.command_input.setStyleSheet("""
            QLineEdit {
                background: rgba(5, 15, 25, 235);
                color: rgb(180, 240, 255);
                border: 1px solid rgb(80, 210, 245);
                border-radius: 8px;
                padding: 8px 12px;
                font-family: Consolas;
                font-size: 14px;
            }

            QLineEdit:focus {
                border: 2px solid rgb(120, 235, 255);
            }
        """)

        self.command_input.returnPressed.connect(
            self.keyboard_command
        )

        # -----------------------------------------------------
        # SPEECH RECOGNITION
        # -----------------------------------------------------

        self.recognizer = sr.Recognizer()

        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8

        try:
            self.microphone = sr.Microphone()
            print("Friday microphone: READY")
        except Exception as e:
            self.microphone = None
            print(
                "Friday microphone: OFFLINE",
                repr(e)
            )

        # -----------------------------------------------------
        # VOICE INITIALIZATION
        # -----------------------------------------------------

        self.setup_voice()

        # -----------------------------------------------------
        # HAND TRACKING
        # -----------------------------------------------------

        self.setup_hand_tracking()

        # -----------------------------------------------------
        # GRAPHICS
        # -----------------------------------------------------

        self.setup_graphics()

        # -----------------------------------------------------
        # TIMER
        # -----------------------------------------------------

        self.timer = QTimer(self)

        self.timer.timeout.connect(
            self.update
        )

        self.timer.start(16)

        # -----------------------------------------------------
        # STARTUP
        # -----------------------------------------------------

        QTimer.singleShot(
            4500,
            self.startup_voice_test
        )

        QTimer.singleShot(
            7000,
            self.start_voice_listener
        )

        print()
        print("=" * 60)
        print(" F.R.I.D.A.Y. 2.0")
        print(" Cinematic Hand Interface")
        print(" Local AI:", self.LLM_MODEL)
        print(" Voice: Microsoft Zira")
        print(" Memory: JSON")
        print(" Camera: MediaPipe")
        print("=" * 60)
        print()

    # =========================================================
    # LOGGING
    # =========================================================

    def log_transcript(self, speaker, text):

        try:
            with open(
                self.TRANSCRIPT_FILE,
                "a",
                encoding="utf-8"
            ) as f:

                timestamp = datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

                f.write(
                    f"[{timestamp}] "
                    f"{speaker}: "
                    f"{text}\n"
                )

        except Exception as e:
            print(
                "Transcript error:",
                repr(e)
            )

    # =========================================================
    # VOICE
    # =========================================================

    # PIPER_AMY_INTEGRATION_V1
    def setup_voice(self):
        self.piper_voice = None
        self.piper_config = None
        self.zira_voice = None

        model = Path(__file__).resolve().parent / "friday_voices" / "en_US-amy-medium.onnx"

        if PiperVoice is not None and model.is_file():
            try:
                print("Friday: Loading Piper Amy...")
                self.piper_voice = PiperVoice.load(str(model))
                self.piper_config = SynthesisConfig(length_scale=0.85)
                print("Friday voice: Piper Amy READY")
            except Exception as e:
                print("Piper initialization error:", repr(e))

        try:
            with self.voice_lock:
                engine = pyttsx3.init()
                engine.setProperty("rate", 175)
                engine.setProperty("volume", 1.0)

                for voice in engine.getProperty("voices") or []:
                    name = str(getattr(voice, "name", "")).lower()
                    voice_id = str(getattr(voice, "id", "")).lower()
                    if "zira" in name or "zira" in voice_id:
                        self.zira_voice = voice.id
                        break

                engine.stop()

            if self.piper_voice is None:
                print("Friday voice: Windows fallback READY")

            self.voice_ready = True

        except Exception as e:
            print("Windows voice initialization error:", repr(e))
            self.voice_ready = self.piper_voice is not None

    def clean_speech(self, text):

        text = str(text)

        # Remove markdown
        text = re.sub(
            r"[*_`#>]",
            "",
            text
        )

        # Remove URLs
        text = re.sub(
            r"https?://\S+",
            "",
            text
        )

        # Remove excessive whitespace
        text = re.sub(
            r"\s+",
            " ",
            text
        )

        return text.strip()

    def speak(self, text):
        text = self.clean_speech(text)

        if not text or not self.voice_ready or not self.voice_running:
            return

        def worker():
            engine = None
            temp_path = None

            with self.voice_lock:
                try:
                    self.voice_busy = True
                    print("Friday:", text)
                    self.log_transcript("FRIDAY", text)

                    if self.piper_voice is not None:
                        try:
                            with tempfile.NamedTemporaryFile(
                                prefix="friday_voice_",
                                suffix=".wav",
                                delete=False,
                            ) as temp:
                                temp_path = temp.name

                            with wave.open(temp_path, "wb") as wav:
                                self.piper_voice.synthesize_wav(
                                    text, wav, syn_config=self.piper_config
                                )

                            winsound.PlaySound(temp_path, winsound.SND_FILENAME)
                            return

                        except Exception as e:
                            print("Piper speech error:", repr(e))
                            print("Switching to Windows speech.")

                        finally:
                            if temp_path:
                                try:
                                    os.unlink(temp_path)
                                except OSError:
                                    pass
                                temp_path = None

                    engine = pyttsx3.init()
                    engine.setProperty("rate", 175)
                    engine.setProperty("volume", 1.0)

                    if self.zira_voice:
                        engine.setProperty("voice", self.zira_voice)

                    engine.say(text)
                    engine.runAndWait()

                except Exception as e:
                    print("VOICE ERROR:", repr(e))

                finally:
                    if engine is not None:
                        try:
                            engine.stop()
                        except Exception:
                            pass
                    self.voice_busy = False

        threading.Thread(target=worker, daemon=True).start()

    def startup_voice_test(self):

        self.speak(
            "AI brain connected, boss."
        )

    # =========================================================
    # VOICE LISTENER
    # =========================================================

    def start_voice_listener(self):

        if self.microphone is None:

            print(
                "Voice listener disabled."
            )

            return

        self.voice_thread = threading.Thread(
            target=self.voice_loop,
            daemon=True
        )

        self.voice_thread.start()

    def voice_loop(self):

        print(
            "Friday voice listener: READY"
        )

        wake_words = [
            "hey friday",
            "hi friday",
            "okay friday",
            "ok friday",
            "friday",
            "freddy",
            "fridie",
            "frady",
            "prady",
        ]

        while self.voice_running:

            try:

                # Prevent Friday hearing herself.
                if self.voice_busy:

                    time.sleep(0.15)

                    continue

                with self.microphone as source:

                    audio = self.recognizer.listen(
                        source,
                        timeout=2,
                        phrase_time_limit=8
                    )

                try:

                    text = (
                        self.recognizer
                        .recognize_google(
                            audio,
                            language="en-IN"
                        )
                        .strip()
                    )

                except sr.UnknownValueError:

                    continue

                except sr.RequestError as e:

                    print(
                        "Speech service error:",
                        repr(e)
                    )

                    time.sleep(2)

                    continue

                if not text:
                    continue

                print(
                    "You:",
                    text
                )

                self.log_transcript(
                    "BOSS",
                    text
                )

                command = text.lower()

                detected_wake = None

                for wake in sorted(
                    wake_words,
                    key=len,
                    reverse=True
                ):

                    if wake in command:

                        detected_wake = wake

                        break

                if detected_wake is None:
                    continue

                command = command.replace(
                    detected_wake,
                    "",
                    1
                ).strip()

                if not command:

                    self.speak(
                        "Yes, boss."
                    )

                    continue

                threading.Thread(
                    target=self.process_text_command,
                    args=(command,),
                    daemon=True
                ).start()

            except sr.WaitTimeoutError:

                continue

            except Exception as e:

                print(
                    "Voice listener error:",
                    repr(e)
                )

                time.sleep(1)

    # =========================================================
    # OLLAMA
    # =========================================================

    def ask_ollama(self, prompt):

        try:

            with self.ai_lock:

                messages = [

                    {
                        "role": "system",
                        "content": (
                            "You are Friday, a local "
                            "personal AI assistant. "
                            "Always call the user boss. "
                            "Never call them sir. "
                            "Be calm, intelligent, concise "
                            "and slightly witty. "
                            "Use short spoken-friendly "
                            "answers. "
                            "Do not say you are Qwen. "
                            "You are Friday."
                        )
                    }

                ]

                messages.extend(
                    self.conversation_history[-10:]
                )

                messages.append(
                    {
                        "role": "user",
                        "content": prompt
                    }
                )

                response = requests.post(

                    self.LLM_URL,

                    json={
                        "model": self.LLM_MODEL,
                        "messages": messages,
                        "stream": False,
                        "think": False,
                        "options": {
                            "temperature": 0.6
                        }
                    },

                    timeout=120
                )

                response.raise_for_status()

                answer = (
                    response.json()
                    .get("message", {})
                    .get("content", "")
                    .strip()
                )

                if not answer:

                    answer = (
                        "I couldn't generate "
                        "a response, boss."
                    )

                self.conversation_history.extend([

                    {
                        "role": "user",
                        "content": prompt
                    },

                    {
                        "role": "assistant",
                        "content": answer
                    }

                ])

                self.conversation_history = (
                    self.conversation_history[-10:]
                )

                return answer

        except Exception as e:

            print(
                "Ollama error:",
                repr(e)
            )

            return (
                "My local reasoning core is offline, "
                "boss. Please make sure Ollama is running."
            )

    # =========================================================
    # MEMORY
    # =========================================================

    def load_memory(self):

        try:

            if not self.MEMORY_FILE.exists():
                return

            with open(
                self.MEMORY_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                data = json.load(f)

            if not isinstance(data, dict):
                return

            for key, value in data.items():

                if isinstance(value, dict):

                    self.memory_data[key] = value

        except Exception as e:

            print(
                "Memory load error:",
                repr(e)
            )

    def save_memory(self):

        try:

            with open(
                self.MEMORY_FILE,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    self.memory_data,
                    f,
                    indent=4,
                    ensure_ascii=False
                )

        except Exception as e:

            print(
                "Memory save error:",
                repr(e)
            )

    def remember(self, text):

        text = text.strip()

        if not text:
            return

        lower = text.lower()

        category = "general"

        if (
            "favorite" in lower
            or
            "i like" in lower
            or
            "i love" in lower
            or
            "prefer" in lower
        ):

            category = "preferences"

        elif (
            "my goal" in lower
            or
            "goal" in lower
        ):

            category = "goals"

        elif (
            "my work" in lower
            or
            "my job" in lower
        ):

            category = "work"

        elif (
            "my computer" in lower
            or
            "my pc" in lower
        ):

            category = "computer"

        elif (
            "i am" in lower
            or
            "i'm" in lower
        ):

            category = "personal"

        key = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S.%f"
        )

        self.memory_data.setdefault(
            category,
            {}
        )[key] = text

        self.save_memory()

    def recall_memory(self):

        memories = []

        for category in self.memory_data.values():

            if isinstance(category, dict):

                memories.extend(
                    str(value)
                    for value in category.values()
                )

        return memories

    def forget_memory(self):

        for key in self.memory_data:

            self.memory_data[key] = {}

        self.save_memory()

    # =========================================================
    # NOTES
    # =========================================================

    def load_notes(self):

        try:

            if not self.NOTES_FILE.exists():
                return

            with open(
                self.NOTES_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                data = json.load(f)

            if isinstance(data, list):

                self.notes = data

        except Exception as e:

            print(
                "Notes load error:",
                repr(e)
            )

    def save_notes(self):

        try:

            with open(
                self.NOTES_FILE,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    self.notes,
                    f,
                    indent=4,
                    ensure_ascii=False
                )

        except Exception as e:

            print(
                "Notes save error:",
                repr(e)
            )

    def add_note(self, text):

        text = text.strip()

        if not text:
            return

        self.notes.append({

            "time":
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),

            "text": text

        })

        self.save_notes()
            # =========================================================
    # SYSTEM / APP / WEB HELPERS
    # =========================================================

    def open_program(self, command, success_message):
        try:
            subprocess.Popen(command)
            self.speak(success_message)
        except Exception as e:
            print("Program launch error:", repr(e))
            self.speak("I couldn't open that, boss.")

    def open_folder(self, folder):
        try:
            os.startfile(str(folder))
            self.speak("Opening it, boss.")
        except Exception as e:
            print("Folder error:", repr(e))
            self.speak("I couldn't open that folder, boss.")

    def google_search(self, query):
        query = query.strip()

        if not query:
            return

        url = (
            "https://www.google.com/search?q="
            + requests.utils.quote(query)
        )

        webbrowser.open(url)

    def image_search(self, query):
        query = query.strip()

        if not query:
            return

        url = (
            "https://www.google.com/search?tbm=isch&q="
            + requests.utils.quote(query)
        )

        webbrowser.open(url)

    def youtube_search(self, query):
        query = query.strip()

        if not query:
            return

        url = (
            "https://www.youtube.com/results?search_query="
            + requests.utils.quote(query)
        )

        webbrowser.open(url)

    def open_url(self, url):
        try:
            if not url.startswith(
                ("http://", "https://")
            ):
                url = "https://" + url

            webbrowser.open(url)

        except Exception as e:
            print("URL error:", repr(e))

    # =========================================================
    # SYSTEM STATUS
    # =========================================================

    def get_system_status(self):

        try:
            cpu = psutil.cpu_percent(
                interval=0.2
            )

            memory = psutil.virtual_memory()

            ram_used = memory.percent

            battery = psutil.sensors_battery()

            if battery:

                battery_text = (
                    f"Battery {battery.percent:.0f} percent"
                )

                if battery.power_plugged:
                    battery_text += ", charging"

            else:

                battery_text = (
                    "Battery information unavailable"
                )

            return (
                f"CPU {cpu:.0f} percent. "
                f"Memory {ram_used:.0f} percent. "
                f"{battery_text}."
            )

        except Exception as e:

            print(
                "System status error:",
                repr(e)
            )

            return (
                "The system is online, boss."
            )

    # =========================================================
    # COMMAND HELP
    # =========================================================

    def capabilities(self):

        return (
            "I can control applications, search Google, "
            "search YouTube and images, control volume and "
            "media, remember information, save notes, "
            "check system status, open folders, lock the PC, "
            "restart or shut down with confirmation, "
            "control the HUD with hand gestures, and answer "
            "questions using my local AI brain, boss."
        )

    # =========================================================
    # MAIN COMMAND ROUTER
    # =========================================================

    def process_text_command(self, text):

        original = str(text).strip()

        if not original:
            return

        command = original.lower().strip()

        print()
        print("COMMAND:", original)

        # -----------------------------------------------------
        # CANCEL
        # -----------------------------------------------------

        if command in (
            "cancel",
            "cancel action",
            "cancel shutdown",
            "cancel restart",
        ):

            self.pending_action = None

            try:
                subprocess.Popen(
                    ["shutdown", "/a"]
                )
            except Exception:
                pass

            self.speak(
                "Cancelled, boss."
            )

            return

        # -----------------------------------------------------
        # SHUTDOWN CONFIRMATION
        # -----------------------------------------------------

        if command in (
            "confirm shutdown",
            "yes shutdown",
            "confirm shut down",
        ):

            if self.pending_action == "shutdown":

                self.pending_action = None

                self.speak(
                    "Shutdown confirmed, boss."
                )

                time.sleep(0.5)

                subprocess.Popen(
                    ["shutdown", "/s", "/t", "5"]
                )

            else:

                self.speak(
                    "There is no pending shutdown, boss."
                )

            return

        # -----------------------------------------------------
        # RESTART CONFIRMATION
        # -----------------------------------------------------

        if command in (
            "confirm restart",
            "yes restart",
        ):

            if self.pending_action == "restart":

                self.pending_action = None

                self.speak(
                    "Restart confirmed, boss."
                )

                time.sleep(0.5)

                subprocess.Popen(
                    ["shutdown", "/r", "/t", "5"]
                )

            else:

                self.speak(
                    "There is no pending restart, boss."
                )

            return

        # =====================================================
        # TIME
        # =====================================================

        if (
            command == "time"
            or "what time is it" in command
            or "tell me the time" in command
        ):

            current_time = datetime.now().strftime(
                "%I:%M %p"
            )

            self.speak(
                f"The time is {current_time}, boss."
            )

            return

        # =====================================================
        # DATE
        # =====================================================

        if (
            command == "date"
            or "what is the date" in command
            or "what's the date" in command
            or "today's date" in command
            or "todays date" in command
        ):

            current_date = datetime.now().strftime(
                "%A, %d %B %Y"
            )

            self.speak(
                f"Today is {current_date}, boss."
            )

            return

        # =====================================================
        # SYSTEM STATUS
        # =====================================================

        if command in (
            "status",
            "system status",
            "system information",
            "system info",
            "check system",
            "how is the system",
        ):

            self.speak(
                self.get_system_status()
            )

            return

        # =====================================================
        # CPU
        # =====================================================

        if (
            command == "cpu"
            or "cpu usage" in command
            or "processor usage" in command
        ):

            try:

                usage = psutil.cpu_percent(
                    interval=0.5
                )

                self.speak(
                    f"CPU usage is "
                    f"{usage:.0f} percent, boss."
                )

            except Exception:

                self.speak(
                    "I couldn't read CPU usage, boss."
                )

            return

        # =====================================================
        # RAM
        # =====================================================

        if (
            command == "ram"
            or "memory usage" in command
            or "ram usage" in command
        ):

            try:

                memory = psutil.virtual_memory()

                self.speak(
                    f"Memory usage is "
                    f"{memory.percent:.0f} percent, boss."
                )

            except Exception:

                self.speak(
                    "I couldn't read memory usage, boss."
                )

            return

        # =====================================================
        # BATTERY
        # =====================================================

        if (
            command == "battery"
            or "battery status" in command
            or "check battery" in command
        ):

            try:

                battery = psutil.sensors_battery()

                if battery:

                    state = (
                        "charging"
                        if battery.power_plugged
                        else "not charging"
                    )

                    self.speak(
                        f"Battery is at "
                        f"{battery.percent:.0f} percent, "
                        f"{state}, boss."
                    )

                else:

                    self.speak(
                        "Battery information is unavailable, boss."
                    )

            except Exception:

                self.speak(
                    "I couldn't read the battery, boss."
                )

            return

        # =====================================================
        # MEMORY â€” REMEMBER
        # =====================================================

        if command.startswith("remember "):

            memory_text = original[
                len("remember "):
            ].strip()

            if memory_text:

                self.remember(
                    memory_text
                )

                self.speak(
                    "I'll remember that, boss."
                )

            return

        # =====================================================
        # MEMORY â€” RECALL
        # =====================================================

        if (
            command == "recall"
            or command == "recall memory"
            or "what do you remember" in command
            or "what do you know about me" in command
        ):

            memories = self.recall_memory()

            if not memories:

                self.speak(
                    "My memory is currently empty, boss."
                )

            else:

                recent = memories[-5:]

                answer = (
                    "I remember "
                    + ". ".join(recent)
                    + ", boss."
                )

                self.speak(answer)

            return

        # =====================================================
        # MEMORY â€” FORGET
        # =====================================================

        if command in (
            "forget everything",
            "forget all",
            "clear memory",
            "delete memory",
            "forget memory",
        ):

            self.forget_memory()

            self.speak(
                "Memory cleared, boss."
            )

            return

        # =====================================================
        # NOTES
        # =====================================================

        note_prefixes = (
            "take note ",
            "make a note ",
            "note ",
            "save note ",
        )

        for prefix in note_prefixes:

            if command.startswith(prefix):

                note_text = original[
                    len(prefix):
                ].strip()

                if note_text:

                    self.add_note(
                        note_text
                    )

                    self.speak(
                        "Note saved, boss."
                    )

                return

        # =====================================================
        # SHOW NOTES
        # =====================================================

        if command in (
            "show notes",
            "read notes",
            "my notes",
            "what are my notes",
        ):

            if not self.notes:

                self.speak(
                    "You have no saved notes, boss."
                )

            else:

                recent_notes = self.notes[-5:]

                text = ". ".join(
                    str(note.get("text", ""))
                    for note in recent_notes
                )

                self.speak(
                    "Your recent notes are "
                    + text
                    + ", boss."
                )

            return

        # =====================================================
        # HELP
        # =====================================================

        if command in (
            "help",
            "what can you do",
            "what can you do for me",
            "capabilities",
        ):

            self.speak(
                self.capabilities()
            )

            return

        # =====================================================
        # CHROME
        # =====================================================

        if command in (
            "open chrome",
            "launch chrome",
            "start chrome",
        ):

            self.open_program(
                [
                    "cmd",
                    "/c",
                    "start",
                    "",
                    "chrome",
                ],
                "Opening Chrome, boss."
            )

            return

        # =====================================================
        # EDGE
        # =====================================================

        if command in (
            "open edge",
            "launch edge",
            "start edge",
        ):

            self.open_program(
                [
                    "cmd",
                    "/c",
                    "start",
                    "",
                    "msedge",
                ],
                "Opening Edge, boss."
            )

            return

        # =====================================================
        # NOTEPAD
        # =====================================================

        if command in (
            "open notepad",
            "launch notepad",
            "start notepad",
        ):

            self.open_program(
                ["notepad.exe"],
                "Opening Notepad, boss."
            )

            return

        # =====================================================
        # CALCULATOR
        # =====================================================

        if command in (
            "open calculator",
            "open calc",
            "launch calculator",
            "start calculator",
        ):

            self.open_program(
                ["calc.exe"],
                "Opening Calculator, boss."
            )

            return

        # =====================================================
        # PAINT
        # =====================================================

        if command in (
            "open paint",
            "launch paint",
            "start paint",
        ):

            self.open_program(
                ["mspaint.exe"],
                "Opening Paint, boss."
            )

            return

        # =====================================================
        # FILE EXPLORER
        # =====================================================

        if command in (
            "open explorer",
            "open file explorer",
            "launch explorer",
            "start explorer",
        ):

            self.open_program(
                ["explorer.exe"],
                "Opening File Explorer, boss."
            )

            return

        # =====================================================
        # SETTINGS
        # =====================================================

        if command in (
            "open settings",
            "launch settings",
            "start settings",
        ):

            self.open_program(
                [
                    "cmd",
                    "/c",
                    "start",
                    "",
                    "ms-settings:"
                ],
                "Opening Settings, boss."
            )

            return

        # =====================================================
        # WORD
        # =====================================================

        if command in (
            "open word",
            "launch word",
            "start word",
            "open microsoft word",
        ):

            self.open_program(
                [
                    "cmd",
                    "/c",
                    "start",
                    "",
                    "winword"
                ],
                "Opening Word, boss."
            )

            return

        # =====================================================
        # EXCEL
        # =====================================================

        if command in (
            "open excel",
            "launch excel",
            "start excel",
            "open microsoft excel",
        ):

            self.open_program(
                [
                    "cmd",
                    "/c",
                    "start",
                    "",
                    "excel"
                ],
                "Opening Excel, boss."
            )

            return

        # =====================================================
        # POWERPOINT
        # =====================================================

        if command in (
            "open powerpoint",
            "launch powerpoint",
            "start powerpoint",
            "open power point",
        ):

            self.open_program(
                [
                    "cmd",
                    "/c",
                    "start",
                    "",
                    "powerpnt"
                ],
                "Opening PowerPoint, boss."
            )

            return

        # =====================================================
        # TASK MANAGER
        # =====================================================

        if command in (
            "open task manager",
            "launch task manager",
            "start task manager",
        ):

            self.open_program(
                ["taskmgr.exe"],
                "Opening Task Manager, boss."
            )

            return

        # =====================================================
        # COMMAND PROMPT
        # =====================================================

        if command in (
            "open command prompt",
            "open cmd",
            "launch command prompt",
            "start command prompt",
        ):

            self.open_program(
                ["cmd.exe"],
                "Opening Command Prompt, boss."
            )

            return

        # =====================================================
        # POWERSHELL
        # =====================================================

        if command in (
            "open powershell",
            "launch powershell",
            "start powershell",
        ):

            self.open_program(
                ["powershell.exe"],
                "Opening PowerShell, boss."
            )

            return

        # =====================================================
        # VS CODE
        # =====================================================

        if command in (
            "open vs code",
            "open vscode",
            "launch vs code",
            "start vs code",
        ):

            self.open_program(
                ["code"],
                "Opening Visual Studio Code, boss."
            )

            return

        # =====================================================
        # FOLDERS
        # =====================================================

        home = Path.home()

        if command in (
            "open desktop",
            "open my desktop",
        ):

            self.open_folder(
                home / "Desktop"
            )

            return

        if command in (
            "open downloads",
            "open my downloads",
        ):

            self.open_folder(
                home / "Downloads"
            )

            return

        if command in (
            "open documents",
            "open my documents",
        ):

            self.open_folder(
                home / "Documents"
            )

            return

        # =====================================================
        # YOUTUBE
        # =====================================================

        if command in (
            "open youtube",
            "launch youtube",
            "start youtube",
        ):

            webbrowser.open(
                "https://www.youtube.com"
            )

            self.speak(
                "Opening YouTube, boss."
            )

            return

        # =====================================================
        # GOOGLE
        # =====================================================

        if command in (
            "open google",
            "launch google",
            "start google",
        ):

            webbrowser.open(
                "https://www.google.com"
            )

            self.speak(
                "Opening Google, boss."
            )

            return

        # =====================================================
        # GITHUB
        # =====================================================

        if command in (
            "open github",
            "launch github",
        ):

            webbrowser.open(
                "https://github.com"
            )

            self.speak(
                "Opening GitHub, boss."
            )

            return

        # =====================================================
        # GOOGLE SEARCH
        # =====================================================

        if command.startswith(
            "search "
        ):

            query = original[
                len("search "):
            ].strip()

            if query:

                self.google_search(
                    query
                )

                self.speak(
                    f"Searching for {query}, boss."
                )

            return

        # =====================================================
        # GOOGLE SEARCH ALTERNATIVE
        # =====================================================

        if command.startswith(
            "google "
        ):

            query = original[
                len("google "):
            ].strip()

            if query:

                self.google_search(
                    query
                )

                self.speak(
                    f"Searching Google for {query}, boss."
                )

            return

        # =====================================================
        # IMAGE SEARCH
        # =====================================================

        if command.startswith(
            "search images "
        ):

            query = original[
                len("search images "):
            ].strip()

            if query:

                self.image_search(
                    query
                )

                self.speak(
                    f"Searching images for {query}, boss."
                )

            return

        # =====================================================
        # YOUTUBE SEARCH
        # =====================================================

        if command.startswith(
            "youtube "
        ):

            query = original[
                len("youtube "):
            ].strip()

            if query:

                self.youtube_search(
                    query
                )

                self.speak(
                    f"Searching YouTube for {query}, boss."
                )

            return

        # =====================================================
        # PLAY SOMETHING
        # =====================================================

        if command.startswith(
            "play "
        ):

            query = original[
                len("play "):
            ].strip()

            if query and query not in (
                "music",
                "pause",
            ):

                self.youtube_search(
                    query
                )

                self.speak(
                    f"Searching YouTube for {query}, boss."
                )

                return

        # =====================================================
        # OPEN WEBSITE
        # =====================================================

        if command.startswith(
            "open website "
        ):

            url = original[
                len("open website "):
            ].strip()

            if url:

                self.open_url(
                    url
                )

                self.speak(
                    "Opening the website, boss."
                )

            return

        # =====================================================
        # LOCK PC
        # =====================================================

        if command in (
            "lock computer",
            "lock pc",
            "lock the computer",
        ):

            self.speak(
                "Locking the computer, boss."
            )

            time.sleep(0.4)

            subprocess.Popen(
                [
                    "rundll32.exe",
                    "user32.dll,LockWorkStation"
                ]
            )

            return

        # =====================================================
        # SHUTDOWN
        # =====================================================

        if (
            command in (
                "shutdown",
                "shut down",
                "shutdown computer",
                "shut down computer",
                "turn off computer",
            )
        ):

            self.pending_action = "shutdown"

            self.speak(
                "Shutdown requires confirmation, boss. "
                "Say confirm shutdown."
            )

            return

        # =====================================================
        # RESTART
        # =====================================================

        if (
            command in (
                "restart",
                "restart computer",
                "restart pc",
                "reboot",
                "reboot computer",
            )
        ):

            self.pending_action = "restart"

            self.speak(
                "Restart requires confirmation, boss. "
                "Say confirm restart."
            )

            return

        # =====================================================
        # VOLUME UP
        # =====================================================

        if (
            command in (
                "volume up",
                "increase volume",
                "turn volume up",
                "louder",
            )
        ):

            for _ in range(5):

                subprocess.Popen(
                    [
                        "powershell",
                        "-Command",
                        (
                            "(New-Object "
                            "-ComObject WScript.Shell)"
                            ".SendKeys([char]175)"
                        )
                    ]
                )

            self.speak(
                "Volume increased, boss."
            )

            return

        # =====================================================
        # VOLUME DOWN
        # =====================================================

        if (
            command in (
                "volume down",
                "decrease volume",
                "turn volume down",
                "quieter",
            )
        ):

            for _ in range(5):

                subprocess.Popen(
                    [
                        "powershell",
                        "-Command",
                        (
                            "(New-Object "
                            "-ComObject WScript.Shell)"
                            ".SendKeys([char]174)"
                        )
                    ]
                )

            self.speak(
                "Volume decreased, boss."
            )

            return

        # =====================================================
        # MUTE
        # =====================================================

        if command in (
            "mute",
            "mute volume",
            "mute sound",
        ):

            subprocess.Popen(
                [
                    "powershell",
                    "-Command",
                    (
                        "(New-Object "
                        "-ComObject WScript.Shell)"
                        ".SendKeys([char]173)"
                    )
                ]
            )

            self.speak(
                "Muted, boss."
            )

            return

        # =====================================================
        # PLAY / PAUSE
        # =====================================================

        if command in (
            "play music",
            "pause music",
            "play pause",
            "pause media",
            "play media",
        ):

            subprocess.Popen(
                [
                    "powershell",
                    "-Command",
                    (
                        "(New-Object "
                        "-ComObject WScript.Shell)"
                        ".SendKeys([char]179)"
                    )
                ]
            )

            self.speak(
                "Done, boss."
            )

            return

        # =====================================================
        # NEXT TRACK
        # =====================================================

        if command in (
            "next song",
            "next track",
            "skip song",
            "skip track",
        ):

            subprocess.Popen(
                [
                    "powershell",
                    "-Command",
                    (
                        "(New-Object "
                        "-ComObject WScript.Shell)"
                        ".SendKeys([char]176)"
                    )
                ]
            )

            self.speak(
                "Next track, boss."
            )

            return

        # =====================================================
        # PREVIOUS TRACK
        # =====================================================

        if command in (
            "previous song",
            "previous track",
            "previous",
        ):

            subprocess.Popen(
                [
                    "powershell",
                    "-Command",
                    (
                        "(New-Object "
                        "-ComObject WScript.Shell)"
                        ".SendKeys([char]177)"
                    )
                ]
            )

            self.speak(
                "Previous track, boss."
            )

            return

        # =====================================================
        # GENERAL OLLAMA AI
        # =====================================================

        answer = self.ask_ollama(
            original
        )

        self.speak(
            answer
        )

    # =========================================================
    # KEYBOARD COMMAND
    # =========================================================

    def keyboard_command(self):

        text = (
            self.command_input
            .text()
            .strip()
        )

        if not text:
            return

        self.command_input.clear()

        print(
            "Keyboard:",
            text
        )

        self.log_transcript(
            "BOSS",
            text
        )

        threading.Thread(
            target=self.process_text_command,
            args=(text,),
            daemon=True
        ).start()
            # =========================================================
    # HAND TRACKING SETUP
    # =========================================================

    def setup_hand_tracking(self):

        try:

            self.mp_hands = mp.solutions.hands

            self.hands = self.mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=1,
                model_complexity=0,
                min_detection_confidence=0.55,
                min_tracking_confidence=0.55
            )

            print(
                "MediaPipe hand tracking: READY"
            )

        except Exception as e:

            self.hands = None

            print(
                "MediaPipe initialization error:",
                repr(e)
            )

    # =========================================================
    # CAMERA LOOP
    # =========================================================

    def camera_loop(self):

        if self.hands is None:

            print(
                "Hand tracking unavailable."
            )

            return

        cap = cv2.VideoCapture(0)

        cap.set(
            cv2.CAP_PROP_FRAME_WIDTH,
            640
        )

        cap.set(
            cv2.CAP_PROP_FRAME_HEIGHT,
            480
        )

        cap.set(
            cv2.CAP_PROP_BUFFERSIZE,
            1
        )

        if not cap.isOpened():

            self.camera_online = False

            print(
                "Camera: OFFLINE"
            )

            return

        self.camera_online = True

        print(
            "Camera: ONLINE"
        )

        print(
            "Hand tracking: ONLINE"
        )

        while self.camera_running:

            success, frame = cap.read()

            if not success:

                self.camera_online = False

                time.sleep(0.05)

                continue

            self.camera_online = True

            # Mirror camera
            frame = cv2.flip(
                frame,
                1
            )

            # Convert BGR -> RGB
            rgb = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB
            )

            try:

                results = (
                    self.hands.process(rgb)
                )

            except Exception as e:

                print(
                    "Hand processing error:",
                    repr(e)
                )

                time.sleep(0.05)

                continue

            # -------------------------------------------------
            # HAND FOUND
            # -------------------------------------------------

            if results.multi_hand_landmarks:

                self.hand_visible = True
                self.hand_online = True

                landmarks = (
                    results
                    .multi_hand_landmarks[0]
                    .landmark
                )

                index_tip = landmarks[
                    self.mp_hands.HandLandmark
                    .INDEX_FINGER_TIP
                ]

                # Smooth movement
                self.hand_x = (
                    self.hand_x * 0.45
                    + index_tip.x * 0.55
                )

                self.hand_y = (
                    self.hand_y * 0.45
                    + index_tip.y * 0.55
                )

                gesture = (
                    self.detect_gesture(
                        landmarks
                    )
                )

                self.gesture = gesture

                if gesture != self.last_gesture:

                    self.last_gesture = gesture

                    self.gesture_time = (
                        time.perf_counter()
                    )

                    self.handle_gesture(
                        gesture
                    )

            # -------------------------------------------------
            # NO HAND
            # -------------------------------------------------

            else:

                self.hand_visible = False
                self.hand_online = False
                self.gesture = "NONE"

            time.sleep(0.005)

        # -----------------------------------------------------
        # CLEANUP
        # -----------------------------------------------------

        cap.release()

        try:

            self.hands.close()

        except Exception:
            pass

        print(
            "Camera thread stopped."
        )

    # =========================================================
    # FINGER DETECTION
    # =========================================================

    def finger_extended(
        self,
        landmarks,
        tip,
        pip,
        mcp
    ):

        wrist = landmarks[
            self.mp_hands.HandLandmark.WRIST
        ]

        def distance(point):

            return math.hypot(
                point.x - wrist.x,
                point.y - wrist.y
            )

        return (
            distance(landmarks[tip])
            >
            distance(landmarks[pip])
            >
            distance(landmarks[mcp])
        )

    # =========================================================
    # GESTURE DETECTION
    # =========================================================

    def detect_gesture(
        self,
        landmarks
    ):

        thumb = self.finger_extended(
            landmarks,

            self.mp_hands.HandLandmark.THUMB_TIP,

            self.mp_hands.HandLandmark.THUMB_IP,

            self.mp_hands.HandLandmark.THUMB_MCP
        )

        index = self.finger_extended(
            landmarks,

            self.mp_hands.HandLandmark.INDEX_FINGER_TIP,

            self.mp_hands.HandLandmark.INDEX_FINGER_PIP,

            self.mp_hands.HandLandmark.INDEX_FINGER_MCP
        )

        middle = self.finger_extended(
            landmarks,

            self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP,

            self.mp_hands.HandLandmark.MIDDLE_FINGER_PIP,

            self.mp_hands.HandLandmark.MIDDLE_FINGER_MCP
        )

        ring = self.finger_extended(
            landmarks,

            self.mp_hands.HandLandmark.RING_FINGER_TIP,

            self.mp_hands.HandLandmark.RING_FINGER_PIP,

            self.mp_hands.HandLandmark.RING_FINGER_MCP
        )

        pinky = self.finger_extended(
            landmarks,

            self.mp_hands.HandLandmark.PINKY_TIP,

            self.mp_hands.HandLandmark.PINKY_PIP,

            self.mp_hands.HandLandmark.PINKY_MCP
        )

        # -----------------------------------------------------
        # THUMBS UP
        # -----------------------------------------------------

        if (
            thumb
            and not index
            and not middle
            and not ring
            and not pinky
        ):

            return "THUMBS UP"

        # -----------------------------------------------------
        # OPEN PALM
        # -----------------------------------------------------

        if (
            thumb
            and index
            and middle
            and ring
            and pinky
        ):

            return "OPEN PALM"

        # -----------------------------------------------------
        # TWO FINGERS
        # -----------------------------------------------------

        if (
            index
            and middle
            and not ring
            and not pinky
        ):

            return "TWO FINGERS"

        # -----------------------------------------------------
        # FIST
        # -----------------------------------------------------

        if (
            not index
            and not middle
            and not ring
            and not pinky
        ):

            return "FIST"

        # -----------------------------------------------------
        # PINCH
        # -----------------------------------------------------

        thumb_tip = landmarks[
            self.mp_hands.HandLandmark.THUMB_TIP
        ]

        index_tip = landmarks[
            self.mp_hands.HandLandmark.INDEX_FINGER_TIP
        ]

        pinch_distance = math.hypot(
            thumb_tip.x - index_tip.x,
            thumb_tip.y - index_tip.y
        )

        if pinch_distance < 0.055:

            return "PINCH"

        # -----------------------------------------------------
        # TRACKING
        # -----------------------------------------------------

        return "TRACKING"

    # =========================================================
    # GESTURE ACTIONS
    # =========================================================

    def handle_gesture(
        self,
        gesture
    ):

        now = time.perf_counter()

        # Prevent repeated gesture triggers
        if (
            now - self.last_action_time
            < 1.0
        ):

            return

        self.last_action_time = now

        # -----------------------------------------------------
        # OPEN PALM
        # -----------------------------------------------------

        if gesture == "OPEN PALM":

            self.speak(
                "HUD active, boss."
            )

            return

        # -----------------------------------------------------
        # THUMBS UP
        # -----------------------------------------------------

        if gesture == "THUMBS UP":

            self.speak(
                "Confirmed, boss."
            )

            return

        # -----------------------------------------------------
        # FIST
        # -----------------------------------------------------

        if gesture == "FIST":

            self.speak(
                "Home position, boss."
            )

            return

        # -----------------------------------------------------
        # TWO FINGERS
        # -----------------------------------------------------

        if gesture == "TWO FINGERS":

            self.speak(
                "Next module, boss."
            )

            return

        # -----------------------------------------------------
        # PINCH
        # -----------------------------------------------------

        if gesture == "PINCH":

            self.speak(
                "Selected, boss."
            )

            return
                # =========================================================
    # CINEMATIC BLACK & WHITE HUD GRAPHICS
    # =========================================================

    def setup_graphics(self):

        # HUD colors
        self.white = (1.0, 1.0, 1.0, 1.0)
        self.grey = (0.55, 0.55, 0.55, 1.0)
        self.dark_grey = (0.22, 0.22, 0.22, 1.0)
        self.black = (0.0, 0.0, 0.0, 1.0)

        # Animation
        self.rotation = 0.0
        self.rotation_inner = 0.0
        self.rotation_outer = 0.0
        self.pulse = 0.0
        self.scan_offset = 0.0
        self.time_started = time.perf_counter()

        # Module system
        self.modules = [
            "SYSTEM",
            "CAMERA",
            "MEMORY",
            "APPS",
            "AI",
            "WEB",
            "NOTES"
        ]

        self.active_module = 0

        # Star field
        random.seed(7)

        self.stars = []

        for _ in range(180):

            self.stars.append({
                "x": random.uniform(-1.0, 1.0),
                "y": random.uniform(-1.0, 1.0),
                "z": random.uniform(0.05, 1.0),
                "size": random.uniform(0.5, 2.0)
            })

        # Reactor points
        self.core_points = []

        for i in range(64):

            angle = (
                (math.pi * 2.0 / 64.0)
                * i
            )

            self.core_points.append(
                (
                    math.cos(angle),
                    math.sin(angle)
                )
            )

        # Command input
        self.command_input.setPlaceholderText(
            "COMMAND // TYPE OR SPEAK"
        )

        self.command_input.setStyleSheet(
            """
            QLineEdit {
                background: rgba(0, 0, 0, 190);
                color: white;
                border: 1px solid rgba(255,255,255,150);
                padding: 8px 12px;
                font-size: 13px;
                font-family: Consolas;
                selection-background-color: white;
                selection-color: black;
            }

            QLineEdit:focus {
                border: 1px solid white;
            }
            """
        )

        self.command_input.returnPressed.connect(
            self.keyboard_command
        )

    # =========================================================
    # OPENGL INITIALIZATION
    # =========================================================

    def initializeGL(self):

        glClearColor(
            0.0,
            0.0,
            0.0,
            1.0
        )

        glEnable(GL_BLEND)

        glBlendFunc(
            GL_SRC_ALPHA,
            GL_ONE_MINUS_SRC_ALPHA
        )

        glEnable(GL_LINE_SMOOTH)

        glHint(
            GL_LINE_SMOOTH_HINT,
            GL_NICEST
        )

        glEnable(GL_POINT_SMOOTH)

        glDisable(GL_DEPTH_TEST)

    # =========================================================
    # RESIZE
    # =========================================================

    def resizeGL(
        self,
        width,
        height
    ):

        if height <= 0:
            height = 1

        glViewport(
            0,
            0,
            width,
            height
        )

        glMatrixMode(
            GL_PROJECTION
        )

        glLoadIdentity()

        aspect = width / float(height)

        if aspect >= 1.0:

            glOrtho(
                -aspect,
                aspect,
                -1.0,
                1.0,
                -10.0,
                10.0
            )

        else:

            glOrtho(
                -1.0,
                1.0,
                -1.0 / aspect,
                1.0 / aspect,
                -10.0,
                10.0
            )

        glMatrixMode(
            GL_MODELVIEW
        )

        glLoadIdentity()

        # Command box
        self.command_input.setGeometry(
            35,
            max(0, height - 62),
            min(430, max(250, width - 70)),
            34
        )

    # =========================================================
    # DRAW LINE CIRCLE
    # =========================================================

    def draw_circle(
        self,
        radius,
        segments=96,
        alpha=1.0
    ):

        glColor4f(
            1.0,
            1.0,
            1.0,
            alpha
        )

        glBegin(
            GL_LINE_LOOP
        )

        for i in range(segments):

            angle = (
                math.pi * 2.0
                * i
                / segments
            )

            glVertex2f(
                math.cos(angle) * radius,
                math.sin(angle) * radius
            )

        glEnd()

    # =========================================================
    # DRAW ARC
    # =========================================================

    def draw_arc(
        self,
        radius,
        start_angle,
        end_angle,
        segments=64,
        alpha=1.0
    ):

        glColor4f(
            1.0,
            1.0,
            1.0,
            alpha
        )

        glBegin(
            GL_LINE_STRIP
        )

        for i in range(segments + 1):

            t = i / float(segments)

            angle = (
                start_angle
                + (end_angle - start_angle)
                * t
            )

            glVertex2f(
                math.cos(angle) * radius,
                math.sin(angle) * radius
            )

        glEnd()

    # =========================================================
    # ROTATING REACTOR
    # =========================================================

    def draw_reactor(self):
        # =====================================================
        # CINEMATIC BLACK & WHITE REACTOR
        # =====================================================

        glPushMatrix()

        # -----------------------------
        # OUTER ROTATING TARGET RING
        # -----------------------------
        glRotatef(
            self.rotation_outer,
            0.0,
            0.0,
            1.0
        )

        self.draw_circle(
            0.54,
            160,
            0.20
        )

        # Outer segmented targeting arcs
        for i in range(12):
            start = math.radians(i * 30.0 + 4.0)
            end = start + math.radians(18.0)

            self.draw_arc(
                0.54,
                start,
                end,
                24,
                0.82
            )

        # Small radial ticks
        glColor4f(
            1.0,
            1.0,
            1.0,
            0.55
        )

        glBegin(GL_LINES)

        for i in range(36):
            angle = math.radians(i * 10.0)

            outer = 0.535
            inner = 0.515

            glVertex2f(
                math.cos(angle) * inner,
                math.sin(angle) * inner
            )

            glVertex2f(
                math.cos(angle) * outer,
                math.sin(angle) * outer
            )

        glEnd()

        glPopMatrix()

        # -----------------------------
        # SECOND ROTATING RING
        # -----------------------------

        glPushMatrix()

        glRotatef(
            -self.rotation_inner,
            0.0,
            0.0,
            1.0
        )

        self.draw_circle(
            0.43,
            128,
            0.30
        )

        for i in range(8):
            start = math.radians(i * 45.0 + 8.0)
            end = start + math.radians(25.0)

            self.draw_arc(
                0.45,
                start,
                end,
                24,
                0.88
            )

        glPopMatrix()

        # -----------------------------
        # INNER PRECISION RING
        # -----------------------------

        glPushMatrix()

        glRotatef(
            self.rotation,
            0.0,
            0.0,
            1.0
        )

        self.draw_circle(
            0.30,
            96,
            0.48
        )

        for i in range(4):
            start = math.radians(i * 90.0 + 12.0)
            end = start + math.radians(52.0)

            self.draw_arc(
                0.31,
                start,
                end,
                20,
                0.72
            )

        glPopMatrix()

        # -----------------------------
        # CROSSHAIR
        # -----------------------------

        glColor4f(
            1.0,
            1.0,
            1.0,
            0.65
        )

        glBegin(GL_LINES)

        # Horizontal
        glVertex2f(-0.70, 0.0)
        glVertex2f(-0.20, 0.0)

        glVertex2f(0.20, 0.0)
        glVertex2f(0.70, 0.0)

        # Vertical
        glVertex2f(0.0, -0.70)
        glVertex2f(0.0, -0.20)

        glVertex2f(0.0, 0.20)
        glVertex2f(0.0, 0.70)

        glEnd()

        # -----------------------------
        # CROSSHAIR CORNER MARKERS
        # -----------------------------

        glColor4f(
            1.0,
            1.0,
            1.0,
            0.85
        )

        glBegin(GL_LINES)

        size = 0.055

        for x, y in [
            (-0.30, 0.30),
            (0.30, 0.30),
            (-0.30, -0.30),
            (0.30, -0.30)
        ]:

            glVertex2f(x - size, y)
            glVertex2f(x + size, y)

            glVertex2f(x, y - size)
            glVertex2f(x, y + size)

        glEnd()

        # -----------------------------
        # PULSING REACTOR CORE
        # -----------------------------

        pulse_size = (
            0.145
            + math.sin(self.pulse) * 0.015
        )

        # Outer glow
        glColor4f(
            1.0,
            1.0,
            1.0,
            0.10
        )

        glBegin(GL_TRIANGLE_FAN)

        glVertex2f(0.0, 0.0)

        for i in range(65):

            angle = (
                math.pi * 2.0
                * i
                / 64.0
            )

            glVertex2f(
                math.cos(angle) * pulse_size,
                math.sin(angle) * pulse_size
            )

        glEnd()

        # Core
        glColor4f(
            1.0,
            1.0,
            1.0,
            0.92
        )

        glBegin(GL_TRIANGLE_FAN)

        glVertex2f(0.0, 0.0)

        for i in range(65):

            angle = (
                math.pi * 2.0
                * i
                / 64.0
            )

            glVertex2f(
                math.cos(angle) * 0.075,
                math.sin(angle) * 0.075
            )

        glEnd()

        # Core outline
        self.draw_circle(
            0.105,
            64,
            0.95
        )

        # Tiny central point
        glPointSize(4.0)

        glColor4f(
            1.0,
            1.0,
            1.0,
            1.0
        )

        glBegin(GL_POINTS)
        glVertex2f(0.0, 0.0)
        glEnd()

    # =========================================================
    # HOLOGRAPHIC GRID
    # =========================================================

    def draw_grid(self):

        glColor4f(
            1.0,
            1.0,
            1.0,
            0.045
        )

        glBegin(
            GL_LINES
        )

        for i in range(-20, 21):

            x = i / 20.0

            glVertex2f(
                x,
                -1.0
            )

            glVertex2f(
                x,
                1.0
            )

            y = i / 20.0

            glVertex2f(
                -1.0,
                y
            )

            glVertex2f(
                1.0,
                y
            )

        glEnd()

    # =========================================================
    # STAR FIELD
    # =========================================================

    def draw_stars(self):

        glPointSize(1.5)

        glBegin(
            GL_POINTS
        )

        for star in self.stars:

            x = star["x"]
            y = star["y"]

            twinkle = (
                0.35
                + 0.25
                * math.sin(
                    self.pulse
                    * 0.8
                    + x * 10.0
                    + y * 7.0
                )
            )

            glColor4f(
                1.0,
                1.0,
                1.0,
                max(
                    0.08,
                    twinkle
                )
            )

            glVertex2f(
                x,
                y
            )

        glEnd()

    # =========================================================
    # HUD CORNER BRACKETS
    # =========================================================

    def draw_corner_brackets(self):

        glColor4f(
            1.0,
            1.0,
            1.0,
            0.55
        )

        glLineWidth(2.0)

        glBegin(
            GL_LINES
        )

        # Top left
        glVertex2f(-0.94, 0.82)
        glVertex2f(-0.82, 0.82)

        glVertex2f(-0.94, 0.82)
        glVertex2f(-0.94, 0.70)

        # Top right
        glVertex2f(0.94, 0.82)
        glVertex2f(0.82, 0.82)

        glVertex2f(0.94, 0.82)
        glVertex2f(0.94, 0.70)

        # Bottom left
        glVertex2f(-0.94, -0.82)
        glVertex2f(-0.82, -0.82)

        glVertex2f(-0.94, -0.82)
        glVertex2f(-0.94, -0.70)

        # Bottom right
        glVertex2f(0.94, -0.82)
        glVertex2f(0.82, -0.82)

        glVertex2f(0.94, -0.82)
        glVertex2f(0.94, -0.70)

        glEnd()

        glLineWidth(1.0)

    # =========================================================
    # SIDE MODULE LINES
    # =========================================================

    def draw_module_lines(self):

        glColor4f(
            1.0,
            1.0,
            1.0,
            0.35
        )

        glBegin(
            GL_LINES
        )

        # Left vertical
        glVertex2f(
            -0.78,
            -0.58
        )

        glVertex2f(
            -0.78,
            0.58
        )

        # Right vertical
        glVertex2f(
            0.78,
            -0.58
        )

        glVertex2f(
            0.78,
            0.58
        )

        # Horizontal connectors
        for y in (
            -0.50,
            -0.25,
            0.0,
            0.25,
            0.50
        ):

            glVertex2f(
                -0.78,
                y
            )

            glVertex2f(
                -0.66,
                y
            )

            glVertex2f(
                0.66,
                y
            )

            glVertex2f(
                0.78,
                y
            )

        glEnd()

    # =========================================================
    # HUD TEXT
    # =========================================================

    def draw_text(
        self,
        painter,
        x,
        y,
        text,
        size=12,
        bold=False,
        opacity=1.0
    ):

        from PyQt6.QtGui import QFont

        font = QFont(
            "Consolas",
            size
        )

        font.setBold(
            bold
        )

        painter.setFont(
            font
        )

        painter.setPen(
            QColor(
                255,
                255,
                255,
                int(
                    255
                    * opacity
                )
            )
        )

        painter.drawText(
            int(x),
            int(y),
            str(text)
        )

    # =========================================================
    # PAINTER HUD OVERLAY
    # =========================================================

    def draw_hud_overlay(
        self
    ):

        painter = QPainter(
            self
        )

        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        width = self.width()
        height = self.height()

        # -----------------------------------------------------
        # TOP TITLE
        # -----------------------------------------------------

        self.draw_text(
            painter,
            35,
            42,
            "F R I D A Y",
            22,
            True,
            1.0
        )

        self.draw_text(
            painter,
            36,
            62,
            "PERSONAL INTELLIGENCE SYSTEM",
            9,
            False,
            0.55
        )

        # -----------------------------------------------------
        # TOP RIGHT STATUS
        # -----------------------------------------------------

        camera_text = (
            "CAMERA ONLINE"
            if self.camera_online
            else "CAMERA OFFLINE"
        )

        hand_text = (
            "HAND TRACKING"
            if self.hand_online
            else "HAND STANDBY"
        )

        voice_text = (
            "VOICE ONLINE"
            if self.voice_ready
            else "VOICE STANDBY"
        )

        self.draw_text(
            painter,
            width - 230,
            38,
            camera_text,
            10,
            True,
            0.85
        )

        self.draw_text(
            painter,
            width - 230,
            56,
            hand_text,
            9,
            False,
            0.60
        )

        self.draw_text(
            painter,
            width - 230,
            73,
            voice_text,
            9,
            False,
            0.60
        )

        # -----------------------------------------------------
        # ACTIVE MODULE
        # -----------------------------------------------------

        module = self.modules[
            self.active_module
            % len(self.modules)
        ]

        self.draw_text(
            painter,
            38,
            height - 105,
            "ACTIVE MODULE",
            9,
            False,
            0.45
        )

        self.draw_text(
            painter,
            38,
            height - 83,
            module,
            16,
            True,
            0.95
        )

        # -----------------------------------------------------
        # GESTURE
        # -----------------------------------------------------

        gesture_text = self.gesture

        self.draw_text(
            painter,
            width - 245,
            height - 105,
            "HAND INTERFACE",
            9,
            False,
            0.45
        )

        self.draw_text(
            painter,
            width - 245,
            height - 83,
            gesture_text,
            14,
            True,
            0.90
        )

        # -----------------------------------------------------
        # CENTER LABEL
        # -----------------------------------------------------

        center_x = width / 2.0

        self.draw_text(
            painter,
            center_x - 65,
            height / 2.0 + 125,
            "REACTOR CORE",
            9,
            False,
            0.50
        )

        # -----------------------------------------------------
        # SYSTEM STATUS
        # -----------------------------------------------------

        self.draw_text(
            painter,
            38,
            95,
            "SYSTEM",
            9,
            False,
            0.45
        )

        self.draw_text(
            painter,
            38,
            113,
            "FRIDAY // ACTIVE",
            11,
            True,
            0.85
        )

        # -----------------------------------------------------
        # VERSION
        # -----------------------------------------------------

        self.draw_text(
            painter,
            width - 170,
            95,
            "FRIDAY 2.0",
            9,
            False,
            0.45
        )

        # -----------------------------------------------------
        # BOTTOM SYSTEM LINE
        # -----------------------------------------------------

        painter.setPen(
            QColor(
                255,
                255,
                255,
                90
            )
        )

        painter.drawLine(
            35,
            height - 125,
            width - 35,
            height - 125
        )

        # -----------------------------------------------------
        # COMMAND HINT
        # -----------------------------------------------------

        self.draw_text(
            painter,
            width / 2.0 - 125,
            height - 32,
            "VOICE / HAND / COMMAND INPUT",
            8,
            False,
            0.40
        )

        painter.end()

    # =========================================================
    # HAND CURSOR
    # =========================================================

    def draw_hand_cursor(
        self
    ):

        if not self.hand_visible:
            return

        # Convert normalized camera position
        # into HUD coordinates.

        x = (
            self.hand_x * 2.0
        ) - 1.0

        y = (
            1.0
            - self.hand_y * 2.0
        )

        glPushMatrix()

        glTranslatef(
            x,
            y,
            0.0
        )

        glRotatef(
            self.rotation * 1.8,
            0.0,
            0.0,
            1.0
        )

        glColor4f(
            1.0,
            1.0,
            1.0,
            0.85
        )

        glLineWidth(
            1.5
        )

        self.draw_circle(
            0.035,
            32,
            0.9
        )

        self.draw_circle(
            0.060,
            32,
            0.35
        )

        glBegin(
            GL_LINES
        )

        glVertex2f(
            -0.09,
            0.0
        )

        glVertex2f(
            -0.045,
            0.0
        )

        glVertex2f(
            0.045,
            0.0
        )

        glVertex2f(
            0.09,
            0.0
        )

        glVertex2f(
            0.0,
            -0.09
        )

        glVertex2f(
            0.0,
            -0.045
        )

        glVertex2f(
            0.0,
            0.045
        )

        glVertex2f(
            0.0,
            0.09
        )

        glEnd()

        glPopMatrix()

        glLineWidth(1.0)

    # =========================================================
    # PAINT EVENT
    # =========================================================

    def paintGL(self):

        current = time.perf_counter()

        elapsed = (
            current
            - self.time_started
        )

        self.rotation = (
            elapsed * 18.0
        )

        self.rotation_inner = (
            elapsed * 30.0
        )

        self.rotation_outer = (
            elapsed * 10.0
        )

        self.pulse = (
            elapsed * 2.8
        )

        self.scan_offset = (
            elapsed * 0.12
        )

        # -----------------------------------------------------
        # CLEAR SCREEN
        # -----------------------------------------------------

        glClear(
            GL_COLOR_BUFFER_BIT
            | GL_DEPTH_BUFFER_BIT
        )

        glMatrixMode(
            GL_MODELVIEW
        )

        glLoadIdentity()

        # -----------------------------------------------------
        # BACKGROUND
        # -----------------------------------------------------

        self.draw_stars()

        self.draw_grid()

        self.draw_corner_brackets()

        self.draw_module_lines()

        # -----------------------------------------------------
        # CENTER REACTOR
        # -----------------------------------------------------

        self.draw_reactor()

        # -----------------------------------------------------
        # HAND CURSOR
        # -----------------------------------------------------

        self.draw_hand_cursor()

        # -----------------------------------------------------
        # 2D HUD
        # -----------------------------------------------------

        self.draw_hud_overlay()

        # -----------------------------------------------------
        # REFRESH
        # -----------------------------------------------------

        self.update()

    # =========================================================
    # MOUSE SUPPORT
    # =========================================================

    def mouseMoveEvent(
        self,
        event
    ):

        self.mouse_x = event.position().x()
        self.mouse_y = event.position().y()

        super().mouseMoveEvent(
            event
        )

    # =========================================================
    # MOUSE CLICK
    # =========================================================

    def mousePressEvent(
        self,
        event
    ):

        if event.button() == (
            Qt.MouseButton.LeftButton
        ):

            self.speak(
                "Selected, boss."
            )

        super().mousePressEvent(
            event
        )

    # =========================================================
    # RESIZE EVENT
    # =========================================================

    def resizeEvent(
        self,
        event
    ):

        super().resizeEvent(
            event
        )

        if hasattr(self, "close_button"):
            self.close_button.move(
                self.width() - self.close_button.width() - 25,
                20
            )
            self.close_button.raise_()

        if hasattr(
            self,
            "command_input"
        ):

            self.command_input.setGeometry(
                35,
                max(
                    0,
                    self.height() - 62
                ),
                min(
                    430,
                    max(
                        250,
                        self.width() - 70
                    )
                ),
                34
            )

    # =========================================================
    # CLOSE EVENT
    # =========================================================

    def closeEvent(
        self,
        event
    ):

        self.camera_running = False
        self.voice_running = False

        try:

            self.hands.close()

        except Exception:
            pass

        event.accept()
            # =========================================================
    # HUD TIMER UPDATE
    # =========================================================

    def update_hud(self):

        # Keep the HUD animated
        self.update()

    # =========================================================
    # MODULE SWITCHING
    # =========================================================

    def next_module(self):

        self.active_module = (
            self.active_module + 1
        ) % len(self.modules)

        module = self.modules[
            self.active_module
        ]

        print(
            "Active module:",
            module
        )

    # =========================================================
    # KEYBOARD SHORTCUTS
    # =========================================================

    def keyPressEvent(
        self,
        event
    ):

        key = event.key()

        # F1 = System
        if key == Qt.Key.Key_F1:

            self.active_module = 0

        # F2 = Camera
        elif key == Qt.Key.Key_F2:

            self.active_module = 1

        # F3 = Memory
        elif key == Qt.Key.Key_F3:

            self.active_module = 2

        # F4 = Apps
        elif key == Qt.Key.Key_F4:

            self.active_module = 3

        # F5 = AI
        elif key == Qt.Key.Key_F5:

            self.active_module = 4

        # F6 = Web
        elif key == Qt.Key.Key_F6:

            self.active_module = 5

        # F7 = Notes
        elif key == Qt.Key.Key_F7:

            self.active_module = 6

        # ESC = stop command input focus
        elif key == Qt.Key.Key_Escape:

            self.command_input.clear()
            self.command_input.clearFocus()

        super().keyPressEvent(
            event
        )


# =============================================================
# APPLICATION ENTRY POINT
# =============================================================

def main():

    print()
    print("=" * 55)
    print("        FRIDAY 2.0 // CINEMATIC HUD")
    print("=" * 55)
    print()

    app = QApplication(
        sys.argv
    )

    # ---------------------------------------------------------
    # DARK APPLICATION PALETTE
    # ---------------------------------------------------------

    app.setStyleSheet(
        """
        QWidget {
            background: black;
            color: white;
        }

        QLineEdit {
            background: black;
            color: white;
        }
        """
    )

    # ---------------------------------------------------------
    # CREATE HUD
    # ---------------------------------------------------------

    window = FridayReelHUD()

    # ---------------------------------------------------------
    # FULL SCREEN
    # ---------------------------------------------------------

    window.showFullScreen()

    # ---------------------------------------------------------
    # START APPLICATION
    # ---------------------------------------------------------

    print()
    print("FRIDAY: ONLINE")
    print("VOICE: READY")
    print("CAMERA: STARTING")
    print("HAND TRACKING: STARTING")
    print("OLLAMA: LOCAL CORE")
    print()
    print("Press ESC to exit command input.")
    print("Close the window to shut down Friday.")
    print()

    sys.exit(
        app.exec()
    )


# =============================================================
# START FRIDAY
# =============================================================

if __name__ == "__main__":

    main()













