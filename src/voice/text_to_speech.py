import subprocess
import threading
import time
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class TextToSpeech:
    def __init__(self):
        self._is_speaking = False
        self.engine = None
        self.use_system_say = False
        self.setup_voice()
    
    def setup_voice(self):
        """Configure TTS engine settings"""
        try:
            # First, try pyttsx3
            import pyttsx3
            logger.info("Attempting to initialize pyttsx3...")
            
            # Try different drivers for pyttsx3
            drivers = [None, 'dummy']  # Try default first, then dummy
            
            for driver in drivers:
                try:
                    logger.info(f"Trying pyttsx3 with driver: {driver}")
                    self.engine = pyttsx3.init(driverName=driver)
                    
                    if self.engine is not None:
                        # Try to configure it
                        self.engine.setProperty('rate', 180)
                        self.engine.setProperty('volume', 0.9)
                        
                        # Get available voices
                        voices = self.engine.getProperty('voices')
                        if voices:
                            # Prefer female voice if available
                            for voice in voices:
                                if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                                    self.engine.setProperty('voice', voice.id)
                                    break
                            else:
                                self.engine.setProperty('voice', voices[0].id)
                        
                        logger.info(f"✅ pyttsx3 initialized successfully with driver: {driver}")
                        return
                        
                except Exception as e:
                    logger.warning(f"pyttsx3 driver '{driver}' failed: {e}")
                    self.engine = None
                    continue
            
            # If pyttsx3 failed, fall back to system 'say' command on macOS
            logger.warning("pyttsx3 failed, trying macOS 'say' command...")
            self._setup_system_say()
            
        except Exception as e:
            logger.error(f"TTS initialization failed: {e}")
            # Try system say as last resort
            self._setup_system_say()
    
    def _setup_system_say(self):
        """Setup macOS system 'say' command as fallback"""
        try:
            # Test if 'say' command is available
            result = subprocess.run(['say', '--version'], 
                                  capture_output=True, timeout=5)
            if result.returncode == 0:
                self.use_system_say = True
                self.engine = "system_say"  # Dummy value to indicate it's working
                logger.info("✅ Using macOS 'say' command for TTS")
            else:
                logger.error("❌ macOS 'say' command not available")
                self.engine = None
        except Exception as e:
            logger.error(f"❌ Failed to setup system say: {e}")
            self.engine = None
    
    def speak(self, text: str, block: bool = True) -> None:
        """Convert text to speech"""
        if not text or not text.strip():
            return
        
        if self.engine is None:
            logger.warning(f"TTS not available, would speak: {text}")
            return
        
        try:
            self._is_speaking = True
            logger.info(f"Speaking: {text}")
            
            if self.use_system_say:
                self._speak_with_system_say(text, block)
            else:
                self._speak_with_pyttsx3(text, block)
                
        except Exception as e:
            logger.error(f"Error in text-to-speech: {e}")
            self._is_speaking = False
    
    def _speak_with_system_say(self, text: str, block: bool):
        """Speak using macOS 'say' command"""
        def speak_async():
            try:
                subprocess.run(['say', text], timeout=30, check=True)
            except Exception as e:
                logger.error(f"System say error: {e}")
            finally:
                self._is_speaking = False
        
        if block:
            speak_async()
        else:
            thread = threading.Thread(target=speak_async)
            thread.daemon = True
            thread.start()
    
    def _speak_with_pyttsx3(self, text: str, block: bool):
        """Speak using pyttsx3"""
        if block:
            self.engine.say(text)
            self.engine.runAndWait()
            self._is_speaking = False
        else:
            def speak_async():
                self.engine.say(text)
                self.engine.runAndWait()
                self._is_speaking = False
            
            thread = threading.Thread(target=speak_async)
            thread.daemon = True
            thread.start()
    
    def is_speaking(self) -> bool:
        """Check if TTS is currently speaking"""
        return self._is_speaking
    
    def stop(self):
        """Stop current speech"""
        try:
            if self.use_system_say:
                subprocess.run(['killall', 'say'], timeout=5)
            elif self.engine and hasattr(self.engine, 'stop'):
                self.engine.stop()
            self._is_speaking = False
        except Exception as e:
            logger.error(f"Error stopping TTS: {e}")
    
    def get_property(self, name):
        """Get TTS property (for compatibility)"""
        if self.use_system_say:
            # Return dummy values for system say
            if name == 'rate':
                return 200
            elif name == 'volume':
                return 0.9
            elif name == 'voices':
                return []
            return None
        elif self.engine and hasattr(self.engine, 'getProperty'):
            return self.engine.getProperty(name)
        return None
    
    def set_property(self, name, value):
        """Set TTS property (for compatibility)"""
        if self.use_system_say:
            # System say doesn't support dynamic property changes
            logger.info(f"System say: ignoring property {name}={value}")
            return
        elif self.engine and hasattr(self.engine, 'setProperty'):
            return self.engine.setProperty(name, value)
