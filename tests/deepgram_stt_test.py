import asyncio, os, sounddevice as sd, numpy as np, wave
import requests, tempfile, time

API_URL = "https://api.deepgram.com/v1/listen?punctuate=true"
API_KEY = os.getenv("DEEPGRAM_API_KEY")

class DeepgramSTT:
    def __init__(self, sr=16000, seconds=5):
        self.sr = sr
        self.seconds = seconds

    def record(self, path):
        print("🎤 Listening...")
        rec = sd.rec(int(self.sr * self.seconds), samplerate=self.sr, dtype='int16', channels=1)
        sd.wait()
        with wave.open(path, 'wb') as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(self.sr)
            wf.writeframes(rec.tobytes())

    def transcribe(self):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            self.record(tmp.name)
            with open(tmp.name, 'rb') as f:
                res = requests.post(API_URL,
                    headers={"Authorization": f"Token {API_KEY}", "Content-Type":"audio/wav"},
                    data=f
                )
        transcript = res.json()["results"]["channels"][0]["alternatives"][0]["transcript"]
        print("📝 You said:", transcript)
        return transcript

if __name__ == "__main__":
    stt = DeepgramSTT()
    stt.transcribe()
