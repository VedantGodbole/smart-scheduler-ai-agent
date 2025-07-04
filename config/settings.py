import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # API Keys
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

    # Deepgram STT    
    DEEPGRAM_API_KEY = os.getenv('DEEPGRAM_API_KEY')

    # Google Calendar
    GOOGLE_CREDENTIALS_PATH = 'credentials/credentials.json'
    GOOGLE_CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID', 'primary')
    
    # Voice Settings
    TTS_ENGINE = os.getenv('TTS_ENGINE', 'pyttsx3')
    STT_ENGINE = os.getenv('STT_ENGINE', 'deepgram')
    
    # Agent Settings
    MAX_CONVERSATION_TURNS = 20
    DEFAULT_MEETING_DURATION = 60  # minutes
    VOICE_RESPONSE_TIMEOUT = 800  # milliseconds
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    @classmethod
    def validate(cls):
        required_settings = ['OPENAI_API_KEY', 'DEEPGRAM_API_KEY']
        missing = [setting for setting in required_settings if not getattr(cls, setting)]
        if missing:
            raise ValueError(f"Missing required settings: {', '.join(missing)}")

settings = Settings()
