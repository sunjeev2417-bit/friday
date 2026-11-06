import threading
import pyttsx3


class FridayVoice:
    def __init__(self):
        self.lock = threading.Lock()
        self.engine = pyttsx3.init()

        self.engine.setProperty("rate", 175)
        self.engine.setProperty("volume", 1.0)

        voices = self.engine.getProperty("voices")

        # Microsoft Zira on normal Windows installations
        selected = None

        for voice in voices:
            name = str(getattr(voice, "name", "")).lower()
            if "zira" in name:
                selected = voice
                break

        if selected is None and len(voices) > 1:
            selected = voices[1]

        if selected is not None:
            self.engine.setProperty("voice", selected.id)

    def speak(self, text):
        if not text:
            return

        with self.lock:
            try:
                self.engine.say(str(text))
                self.engine.runAndWait()
            except Exception as e:
                print("Voice error:", e)


_voice = FridayVoice()


def speak(text):
    _voice.speak(text)


if __name__ == "__main__":
    print("Friday voice: ONLINE")
    speak("Voice system online, boss.")
