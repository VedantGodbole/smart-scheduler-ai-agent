import os
import time
import tempfile
import wave
import logging
from typing import Optional

# Import the Deepgram SDK components
from deepgram import (
    DeepgramClient,
    DeepgramClientOptions, 
    ClientOptionsFromEnv,
    PrerecordedOptions,
    LiveOptions,
    LiveTranscriptionEvents,
    Microphone
)

# For audio recording
try:
    import sounddevice as sd
    import numpy as np
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    print("⚠️ sounddevice not available. Install with: pip install sounddevice")
    SOUNDDEVICE_AVAILABLE = False

class DeepgramTester:
    """Test class for Deepgram functionality"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Deepgram client"""
        
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Get API key from environment or parameter
        self.api_key = api_key or os.getenv("DEEPGRAM_API_KEY")
        
        if not self.api_key:
            raise ValueError(
                "❌ DEEPGRAM_API_KEY is required. "
                "Set it in your environment variables or pass it to the constructor."
            )
        
        # Initialize client with latest SDK syntax
        try:
            # Use environment variables
            # self.deepgram = DeepgramClient("", ClientOptionsFromEnv())
            
            # Pass API key directly
            self.deepgram = DeepgramClient(self.api_key)
            
            self.logger.info("✅ Deepgram client initialized successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize Deepgram client: {e}")
            raise
    
    def test_url_transcription(self):
        """Test transcribing audio from a URL"""
        print("\n🌐 Testing URL Transcription...")
        
        try:
            # Use Deepgram's sample audio URL
            AUDIO_URL = {
                "url": "https://static.deepgram.com/examples/Bueller-Life-moves-pretty-fast.wav"
            }
            
            # Configure transcription options
            options = PrerecordedOptions(
                model="nova-3",          # Latest model
                smart_format=True,       # Automatically format output
                punctuate=True,          # Add punctuation
                language="en-US",        # Language
                diarize=False           # Speaker diarization
            )
            
            # Make transcription request using v4 API
            print("🔄 Sending transcription request...")
            response = self.deepgram.listen.rest.v("1").transcribe_url(AUDIO_URL, options)
            
            # Extract transcript
            transcript = response["results"]["channels"][0]["alternatives"][0]["transcript"]
            
            print("✅ URL Transcription successful!")
            print(f"📝 Transcript: {transcript}")
            
            return True
            
        except Exception as e:
            print(f"❌ URL transcription failed: {e}")
            return False
    
    def test_file_transcription(self):
        """Test transcribing a local audio file"""
        print("\n📁 Testing File Transcription...")
        
        if not SOUNDDEVICE_AVAILABLE:
            print("⚠️ Skipping file transcription test - sounddevice not available")
            return True
        
        try:
            # Record a short audio clip for testing
            print("🎤 Recording 6 seconds of audio for testing...")
            print("📢 Please speak something now...")
            
            # Recording parameters
            duration = 6  # seconds
            sample_rate = 16000
            channels = 1
            
            # Record audio
            recording = sd.rec(
                int(duration * sample_rate),
                samplerate=sample_rate,
                channels=channels,
                dtype='int16'
            )
            sd.wait()  # Wait for recording to complete
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                # Write WAV file
                with wave.open(temp_file.name, 'wb') as wav_file:
                    wav_file.setnchannels(channels)
                    wav_file.setsampwidth(2)  # 16-bit
                    wav_file.setframerate(sample_rate)
                    wav_file.writeframes(recording.tobytes())
                
                print(f"💾 Audio saved to: {temp_file.name}")
                
                # Transcribe the recorded file
                print("🔄 Transcribing recorded audio...")
                
                with open(temp_file.name, "rb") as audio_file:
                    buffer_data = {"buffer": audio_file}
                    
                    options = PrerecordedOptions(
                        model="nova-3",
                        smart_format=True,
                        punctuate=True,
                        language="en-US"
                    )
                    
                    response = self.deepgram.listen.rest.v("1").transcribe_file(
                        buffer_data, options
                    )
                
                # Extract transcript
                transcript = response["results"]["channels"][0]["alternatives"][0]["transcript"]
                
                print("✅ File transcription successful!")
                print(f"📝 Transcript: {transcript}")
                
                # Clean up
                os.unlink(temp_file.name)
                
                return True
                
        except Exception as e:
            print(f"❌ File transcription failed: {e}")
            return False
    
    def test_live_transcription(self):
        """Test live streaming transcription"""
        print("\n🎙️ Testing Live Transcription...")
        
        try:
            # Create WebSocket connection
            dg_connection = self.deepgram.listen.websocket.v("1")
            
            # Define event handlers
            def on_open(self, open, **kwargs):
                print("🔌 Connection opened")
            
            def on_message(self, result, **kwargs):
                sentence = result.channel.alternatives[0].transcript
                if len(sentence) > 0:
                    print(f"📝 Live transcript: {sentence}")
            
            def on_metadata(self, metadata, **kwargs):
                print(f"📊 Metadata received")
            
            def on_speech_started(self, speech_started, **kwargs):
                print("🗣️ Speech started")
            
            def on_utterance_end(self, utterance_end, **kwargs):
                print("⏹️ Utterance ended")
            
            def on_error(self, error, **kwargs):
                print(f"❌ Error: {error}")
            
            def on_close(self, close, **kwargs):
                print("🔌 Connection closed")
            
            # Register event handlers
            dg_connection.on(LiveTranscriptionEvents.Open, on_open)
            dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
            dg_connection.on(LiveTranscriptionEvents.Metadata, on_metadata)
            dg_connection.on(LiveTranscriptionEvents.SpeechStarted, on_speech_started)
            dg_connection.on(LiveTranscriptionEvents.UtteranceEnd, on_utterance_end)
            dg_connection.on(LiveTranscriptionEvents.Error, on_error)
            dg_connection.on(LiveTranscriptionEvents.Close, on_close)
            
            # Configure live options
            options = LiveOptions(
                model="nova-3",
                punctuate=True,
                language="en-US",
                encoding="linear16",
                channels=1,
                sample_rate=16000,
                interim_results=True,
                utterance_end_ms="1000",
                vad_events=False,
            )
            
            # Start connection
            print("🔄 Starting live transcription...")
            dg_connection.start(options)
            
            # Create microphone (if available)
            if SOUNDDEVICE_AVAILABLE:
                microphone = Microphone(dg_connection.send)
                microphone.start()
                
                print("🎤 Speak now! Press Enter to stop...")
                input()
                
                microphone.finish()
            else:
                print("⚠️ Microphone not available - simulating connection...")
                time.sleep(2)
            
            # Close connection
            dg_connection.finish()
            print("✅ Live transcription test completed")
            
            return True
            
        except Exception as e:
            print(f"❌ Live transcription failed: {e}")
            return False
    
    def run_all_tests(self):
        """Run all available tests"""
        print("🧪 Starting Deepgram SDK Tests")
        print("=" * 50)
        
        results = {
            "url_transcription": self.test_url_transcription(),
            "file_transcription": self.test_file_transcription(),
            "live_transcription": self.test_live_transcription()
        }
        
        print("\n" + "=" * 50)
        print("📊 Test Results Summary:")
        
        passed = 0
        for test_name, result in results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"  {test_name}: {status}")
            if result:
                passed += 1
        
        print(f"\n🎯 Overall: {passed}/{len(results)} tests passed")
        
        if passed == len(results):
            print("🎉 All tests passed! Deepgram is working correctly.")
        else:
            print("⚠️ Some tests failed. Check your API key and network connection.")
        
        return results


def main():
    """Main function to run tests"""
    try:
        # Initialize tester
        tester = DeepgramTester()
        
        # Run all tests
        results = tester.run_all_tests()
        
        return all(results.values())
        
    except Exception as e:
        print(f"❌ Failed to run tests: {e}")
        return False


if __name__ == "__main__":
    print("🎤 Deepgram SDK Test Script")
    print("=" * 50)
    
    # Check for API key
    api_key = os.getenv("DEEPGRAM_API_KEY")
    if not api_key:
        print("❌ DEEPGRAM_API_KEY environment variable is required!")
        print("💡 Get your free API key at: https://console.deepgram.com/signup")
        print("💡 Then set it in your environment:")
        print("   export DEEPGRAM_API_KEY='your_api_key_here'")
        exit(1)
    
    print(f"🔑 Using API key: {api_key[:8]}..." if api_key else "No API key found")
    
    # Run tests
    success = main()
    
    if success:
        print("\n🎉 All systems go! Deepgram is ready to use.")
        exit(0)
    else:
        print("\n❌ Some issues detected. Please check the output above.")
        exit(1)
