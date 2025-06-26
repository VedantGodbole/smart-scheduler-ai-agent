import unittest
from unittest.mock import Mock, patch, MagicMock
from src.voice.speech_to_text import SpeechToText
from src.voice.text_to_speech import TextToSpeech

class TestSpeechToText(unittest.TestCase):
    def setUp(self):
        with patch('speech_recognition.Microphone'), \
             patch('speech_recognition.Recognizer'):
            self.stt = SpeechToText()
    
    @patch('speech_recognition.Recognizer.listen')
    @patch('speech_recognition.Recognizer.recognize_google')
    def test_listen_and_transcribe_success(self, mock_recognize, mock_listen):
        """Test successful speech transcription"""
        mock_audio = Mock()
        mock_listen.return_value = mock_audio
        mock_recognize.return_value = "Hello, I need to schedule a meeting"
        
        # Mock the instance methods instead of class methods
        self.stt.recognizer.listen = mock_listen
        self.stt.recognizer.recognize_google = mock_recognize
        
        result = self.stt.listen_and_transcribe()
        self.assertEqual(result, "Hello, I need to schedule a meeting")
    
    def test_listen_timeout(self):
        """Test timeout handling"""
        import speech_recognition as sr
        
        # Mock the instance methods to raise WaitTimeoutError
        self.stt.recognizer.listen = Mock(side_effect=sr.WaitTimeoutError())
        
        result = self.stt.listen_and_transcribe()
        self.assertIsNone(result)
    
    def test_microphone_availability(self):
        """Test microphone availability check"""
        # This test might need to be adjusted based on actual hardware
        availability = self.stt.is_microphone_available()
        self.assertIsInstance(availability, bool)

class TestTextToSpeech(unittest.TestCase):
    def setUp(self):
        with patch('pyttsx3.init'):
            self.tts = TextToSpeech()
            self.tts.engine = Mock()
    
    def test_speak_text(self):
        """Test text-to-speech functionality"""
        test_text = "Hello, this is a test"
        self.tts.speak(test_text, block=False)
        
        # Verify that the engine methods were called
        self.tts.engine.say.assert_called_with(test_text)
    
    def test_speak_empty_text(self):
        """Test handling of empty text"""
        self.tts.speak("", block=False)
        self.tts.engine.say.assert_not_called()
    
    def test_is_speaking(self):
        """Test speaking status tracking"""
        initial_status = self.tts.is_speaking()
        self.assertIsInstance(initial_status, bool)
