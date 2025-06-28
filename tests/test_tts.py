import pyttsx3
import platform
import subprocess

def test_pyttsx3():
    try:
        print("🔊 Testing pyttsx3...")
        engine = pyttsx3.init()
        engine.say("Hello! This is a test of pyttsx3 text to speech.")
        engine.runAndWait()
        print("✅ pyttsx3 is working.")
    except Exception as e:
        print("❌ pyttsx3 failed:", e)

def test_system_say():
    try:
        print("🔊 Testing system 'say' command...")
        if platform.system() == "Darwin":  # macOS
            subprocess.run(["say", "Hello from system TTS!"])
            print("✅ System TTS is working.")
        else:
            print("⚠️ 'say' command not available on this OS.")
    except Exception as e:
        print("❌ System 'say' failed:", e)

if __name__ == "__main__":
    test_pyttsx3()
    test_system_say()
