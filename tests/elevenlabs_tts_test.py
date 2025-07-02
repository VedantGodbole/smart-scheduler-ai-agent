from elevenlabs import ElevenLabs, play
import os

ELEVEN_API_KEY = os.getenv("ELEVENLABS_API_KEY")

class ElevenLabsTTS:
    def __init__(self, voice_id="9BWtsMINqrJLrRacOk9x", model="eleven_turbo_v2_5"):
        self.client = ElevenLabs(api_key=ELEVEN_API_KEY)
        self.voice_id = voice_id
        self.model = model

    def speak(self, text: str):
        if not text:
            return
        print(f"🔊 Speaking: {text}")
        audio = self.client.text_to_speech.convert(
            voice_id=self.voice_id,
            text=text,
            model_id=self.model,
            output_format="mp3_22050_32"
        )
        play(audio)

if __name__ == "__main__":
    tts = ElevenLabsTTS()
    tts.speak("Hello Vedant! Your ElevenLabs voice is now fully working.")
