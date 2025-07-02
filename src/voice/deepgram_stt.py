# src/voice/deepgram_stt.py
import asyncio
import os
import tempfile
import wave
import sounddevice as sd
from deepgram import DeepgramClient, PrerecordedOptions
from typing import Optional
import concurrent.futures
import logging

logger = logging.getLogger(__name__)

class DeepgramSTT:
    def __init__(self, record_seconds=5, sample_rate=16000):
        self.record_seconds = record_seconds
        self.sample_rate = sample_rate
        self.channels = 1
        
        # Initialize Deepgram client with API key from environment
        api_key = os.getenv("DEEPGRAM_API_KEY")
        if not api_key:
            raise ValueError("DEEPGRAM_API_KEY environment variable is required")
        
        self.deepgram = DeepgramClient(api_key)

    def _record_audio(self, file_path):
        """Record audio to file"""
        print("🎤 Listening...")
        recording = sd.rec(int(self.sample_rate * self.record_seconds),
                           samplerate=self.sample_rate,
                           channels=self.channels,
                           dtype='int16')
        sd.wait()

        with wave.open(file_path, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(recording.tobytes())

    async def transcribe_async(self):
        """Async transcription using Deepgram SDK v4+"""
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmpfile:
                self._record_audio(tmpfile.name)

                with open(tmpfile.name, "rb") as audio:
                    # Updated for SDK v4+ API
                    payload = {"buffer": audio}
                    
                    # Configure transcription options
                    options = PrerecordedOptions(
                        model="nova-3",  # Latest model
                        punctuate=True,
                        language="en-US",
                        smart_format=True
                    )
                    
                    # Make transcription request
                    response = await self.deepgram.listen.asyncprerecorded.v("1").transcribe_file(
                        payload, options
                    )
                    
                    # Extract transcript from response
                    transcript = response["results"]["channels"][0]["alternatives"][0]["transcript"]
                    print(f"📝 You said: {transcript}")
                    
                    # Clean up temp file
                    os.unlink(tmpfile.name)
                    
                    return transcript
                    
        except Exception as e:
            logger.error(f"Deepgram transcription error: {e}")
            return None

    def listen_and_transcribe(self, timeout: float = 5.0, phrase_time_limit: float = 10.0) -> Optional[str]:
        """Synchronous wrapper for compatibility with existing code"""
        try:
            # Update record_seconds based on phrase_time_limit
            original_record_seconds = self.record_seconds
            self.record_seconds = min(phrase_time_limit, self.record_seconds)
            
            # Handle async in sync context
            try:
                # Check if there's already a running event loop
                loop = asyncio.get_running_loop()
                # If there is, run in thread pool
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(self._run_in_new_loop)
                    result = future.result(timeout=timeout)
                    return result
            except RuntimeError:
                # No running loop, safe to create new one
                return asyncio.run(self.transcribe_async())
            finally:
                self.record_seconds = original_record_seconds
                
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return None

    def _run_in_new_loop(self):
        """Helper to run async code in new event loop (for thread pool)"""
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            return new_loop.run_until_complete(self.transcribe_async())
        finally:
            new_loop.close()

    def is_microphone_available(self) -> bool:
        """Check if microphone is available"""
        try:
            # Test very short recording
            test_recording = sd.rec(int(self.sample_rate * 0.1),
                                   samplerate=self.sample_rate,
                                   channels=self.channels,
                                   dtype='int16')
            sd.wait()
            return True
        except Exception as e:
            logger.error(f"Microphone not available: {e}")
            return False
