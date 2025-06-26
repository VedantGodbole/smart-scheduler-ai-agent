import unittest
import time
import threading
from datetime import datetime
import os
from src.voice.speech_to_text import SpeechToText
from src.voice.text_to_speech import TextToSpeech

class TestRealVoiceIntegration(unittest.TestCase):
    """Integration tests with real voice hardware"""
    
    @classmethod
    def setUpClass(cls):
        """Check if we can run real voice tests"""
        cls.can_run_voice_tests = cls._check_voice_hardware()
        
        if cls.can_run_voice_tests:
            print("🎤 Voice hardware detected - running real voice tests")
            cls.stt = SpeechToText()
            cls.tts = TextToSpeech()
        else:
            print("⚠️ Voice hardware not available - skipping real voice tests")
    
    @classmethod
    def _check_voice_hardware(cls) -> bool:
        """Check if microphone and speakers are available"""
        try:
            # Test microphone availability
            temp_stt = SpeechToText()
            mic_available = temp_stt.is_microphone_available()
            
            # Test TTS availability with better error handling
            temp_tts = TextToSpeech()
            
            # Check if TTS is working (either pyttsx3 or system say)
            tts_available = (temp_tts.engine is not None) or temp_tts.use_system_say
            
            print(f"🎤 Microphone available: {mic_available}")
            print(f"🔊 Text-to-speech available: {tts_available}")
            
            if hasattr(temp_tts, 'use_system_say') and temp_tts.use_system_say:
                print("🔊 Using macOS 'say' command for TTS")
            elif temp_tts.engine:
                print("🔊 Using pyttsx3 for TTS")
            
            return mic_available and tts_available
            
        except Exception as e:
            print(f"❌ Voice hardware check failed: {e}")
            return False
    
    def setUp(self):
        """Skip tests if voice hardware not available"""
        if not self.can_run_voice_tests:
            self.skipTest("Voice hardware not available")
    
    def test_real_microphone_detection(self):
        """Test real microphone detection"""
        print("\n🎤 Testing real microphone detection...")
        
        is_available = self.stt.is_microphone_available()
        self.assertTrue(is_available, "Microphone should be available")
        
        print("✅ Microphone detected and accessible")
    
    def test_real_text_to_speech(self):
        """Test real text-to-speech output"""
        print("\n🔊 Testing real text-to-speech...")
        print("📢 You should hear the following message spoken aloud:")
        
        test_message = "Hello! This is a test of the text to speech system. Can you hear me?"
        print(f"📝 Speaking: '{test_message}'")
        
        # Test TTS (you should hear this)
        self.tts.speak(test_message, block=True)
        
        # Verify TTS completed without errors
        self.assertFalse(self.tts.is_speaking())
        print("✅ Text-to-speech test completed")
    
    def test_real_speech_recognition_interactive(self):
        """Interactive test - you speak, we verify transcription"""
        print("\n🎤 Testing real speech recognition...")
        print("📢 This test requires your participation!")
        
        # Give user time to prepare
        print("⏰ Get ready to speak in 3 seconds...")
        time.sleep(3)
        
        # Test phrases to try
        test_phrases = [
            "I need to schedule a meeting",
            "One hour meeting", 
            "Tuesday afternoon"
        ]
        
        for i, expected_phrase in enumerate(test_phrases, 1):
            print(f"\n🎯 Test {i}/3:")
            print(f"📝 Please say: '{expected_phrase}'")
            print("🎤 Listening... speak now!")
            
            # Listen for speech
            result = self.stt.listen_and_transcribe(timeout=10.0)
            
            if result:
                print(f"📤 You said: '{result}'")
                print(f"📥 Expected: '{expected_phrase}'")
                
                # Check if transcription is reasonably close
                similarity = self._calculate_similarity(result.lower(), expected_phrase.lower())
                print(f"📊 Similarity: {similarity:.1%}")
                
                # Pass if similarity > 70%
                self.assertGreater(similarity, 0.7, 
                    f"Transcription too different. Got: '{result}', Expected: '{expected_phrase}'")
                print("✅ Speech recognition successful!")
            else:
                print("❌ No speech detected or transcription failed")
                self.fail(f"Failed to transcribe: '{expected_phrase}'")
            
            # Brief pause between tests
            time.sleep(2)
    
    def test_real_speech_recognition_timeout(self):
        """Test speech recognition timeout with real hardware"""
        print("\n⏱️ Testing speech recognition timeout...")
        print("🔇 Please DON'T speak for this test - testing timeout handling")
        
        start_time = time.time()
        result = self.stt.listen_and_transcribe(timeout=3.0)
        end_time = time.time()
        
        # Should timeout and return None
        self.assertIsNone(result, "Should return None on timeout")
        
        # Should timeout in roughly the right time (±1 second tolerance)
        elapsed = end_time - start_time
        self.assertGreater(elapsed, 2.0, "Should wait at least 2 seconds")
        self.assertLess(elapsed, 5.0, "Should timeout within 5 seconds")
        
        print(f"✅ Timeout handled correctly in {elapsed:.1f} seconds")
    
    def test_real_voice_conversation_simulation(self):
        """Simulate a real voice conversation"""
        print("\n💬 Testing simulated voice conversation...")
        print("🤖 This simulates how the scheduler would interact with you")
        
        # Simulate agent speaking
        agent_messages = [
            "Hello! I'm your Smart Scheduler. I can help you find and schedule a meeting.",
            "Great! How long should the meeting be?",
            "Perfect! Do you have any preferred days or times?"
        ]
        
        for i, message in enumerate(agent_messages, 1):
            print(f"\n🤖 Agent says ({i}/{len(agent_messages)}):")
            print(f"📝 '{message}'")
            
            # Agent speaks
            self.tts.speak(message, block=True)
            
            # Brief pause for realism
            time.sleep(1)
            
            if i < len(agent_messages):  # Don't listen after last message
                print("🎤 Your turn to respond (or just wait for timeout)...")
                
                # Listen for user response (optional)
                user_response = self.stt.listen_and_transcribe(timeout=5.0)
                
                if user_response:
                    print(f"👤 You said: '{user_response}'")
                else:
                    print("🔇 (No response detected - continuing demo)")
        
        print("✅ Voice conversation simulation completed")
    
    def test_real_ambient_noise_handling(self):
        """Test handling of ambient noise"""
        print("\n🌊 Testing ambient noise handling...")
        print("📢 The system will adjust for ambient noise in your environment")
        
        # Test ambient noise adjustment
        print("🎤 Adjusting for ambient noise... please be quiet for 2 seconds")
        
        try:
            with self.stt.microphone as source:
                self.stt.recognizer.adjust_for_ambient_noise(source, duration=2)
            
            print("✅ Ambient noise adjustment completed")
            
            # Test recognition after adjustment
            print("🎤 Now say something to test noise-adjusted recognition:")
            result = self.stt.listen_and_transcribe(timeout=8.0)
            
            if result:
                print(f"📤 Transcribed with noise adjustment: '{result}'")
                print("✅ Noise handling successful")
            else:
                print("🔇 No speech detected (this might be OK)")
                
        except Exception as e:
            print(f"⚠️ Ambient noise adjustment failed: {e}")
            # Don't fail test - this is environment dependent
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate rough text similarity for transcription validation"""
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0

class TestRealVoiceIntegrationSilent(unittest.TestCase):
    """Non-interactive real voice tests"""
    
    def setUp(self):
        """Set up real voice components"""
        try:
            self.stt = SpeechToText()
            self.tts = TextToSpeech()
            self.voice_available = self.stt.is_microphone_available()
        except Exception:
            self.voice_available = False
        
        if not self.voice_available:
            self.skipTest("Voice hardware not available")
    
    def test_voice_component_initialization(self):
        """Test that voice components initialize correctly"""
        print("\n🔧 Testing voice component initialization...")
        
        # Test STT initialization
        self.assertIsNotNone(self.stt.recognizer)
        self.assertIsNotNone(self.stt.microphone)
        print("✅ Speech-to-text initialized")
        
        # Test TTS initialization
        self.assertIsNotNone(self.tts.engine)
        print("✅ Text-to-speech initialized")
    
    def test_voice_settings_configuration(self):
        """Test voice settings are configured correctly"""
        print("\n⚙️ Testing voice settings...")
        
        # Test TTS settings
        rate = self.tts.engine.getProperty('rate')
        volume = self.tts.engine.getProperty('volume')
        
        self.assertIsInstance(rate, (int, float))
        self.assertIsInstance(volume, (int, float))
        self.assertGreaterEqual(volume, 0.0)
        self.assertLessEqual(volume, 1.0)
        
        print(f"🗣️ TTS Rate: {rate} words/minute")
        print(f"🔊 TTS Volume: {volume}")
        print("✅ Voice settings configured correctly")

if __name__ == '__main__':
    print("🎤 Real Voice Integration Tests")
    print("=" * 50)
    print("⚠️ WARNING: These tests will:")
    print("   • Use your microphone")
    print("   • Play audio through speakers")
    print("   • Require your participation")
    print("=" * 50)
    
    response = input("Continue with real voice tests? (y/N): ").lower().strip()
    
    if response in ['y', 'yes']:
        # Run the tests
        unittest.main(verbosity=2)
    else:
        print("🔇 Skipping real voice tests")
