import platform
import subprocess
import logging

logger = logging.getLogger(__name__)

class TextToSpeech:
    def __init__(self):
        self.use_system_say = platform.system() == "Darwin"
        self.engine = None

        if not self.use_system_say:
            try:
                import pyttsx3
                self.engine = pyttsx3.init()
                logger.info("✅ pyttsx3 initialized successfully.")
            except Exception as e:
                logger.warning(f"⚠️ pyttsx3 initialization failed: {e}")
                self.engine = None
        else:
            logger.info("✅ Using macOS system TTS via 'say' command.")

    def speak(self, text: str, block: bool = True):
        if self.use_system_say:
            try:
                logger.info(f"Speaking via 'say': {text}")
                subprocess.run(["say", text])
            except Exception as e:
                logger.error(f"System 'say' failed: {e}")
        elif self.engine:
            try:
                logger.info(f"Speaking via pyttsx3: {text}")
                self.engine.say(text)
                if block:
                    self.engine.runAndWait()
            except Exception as e:
                logger.error(f"pyttsx3 speak failed: {e}")
        else:
            logger.error("❌ No TTS engine available to speak.")
