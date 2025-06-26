import speech_recognition as sr
from typing import Optional
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class SpeechToText:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Adjust for ambient noise
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)
    
    def listen_and_transcribe(self, timeout: float = 5.0, phrase_time_limit: float = 10.0) -> Optional[str]:
        """Listen to microphone and transcribe speech"""
        try:
            logger.info("Listening for speech...")
            
            with self.microphone as source:
                # Listen for audio with timeout
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            
            logger.info("Transcribing speech...")
            
            # Use Google Speech Recognition
            text = self.recognizer.recognize_google(audio)
            logger.info(f"Transcribed: {text}")
            return text
            
        except sr.WaitTimeoutError:
            logger.warning("No speech detected within timeout")
            return None
        except sr.UnknownValueError:
            logger.warning("Could not understand audio")
            return None
        except sr.RequestError as e:
            logger.error(f"Speech recognition service error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in speech recognition: {e}")
            return None
    
    def is_microphone_available(self) -> bool:
        """Check if microphone is available"""
        try:
            with self.microphone as source:
                pass
            return True
        except Exception as e:
            logger.error(f"Microphone not available: {e}")
            return False
