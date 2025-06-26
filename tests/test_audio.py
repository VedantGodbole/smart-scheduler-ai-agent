import speech_recognition as sr

def test_microphone():
    r = sr.Recognizer()
    mic = sr.Microphone()
    
    print("Available microphones:")
    for index, name in enumerate(sr.Microphone.list_microphone_names()):
        print(f"  {index}: {name}")
    
    print("\nTesting microphone access...")
    try:
        with mic as source:
            print("✅ Microphone accessible")
            r.adjust_for_ambient_noise(source, duration=1)
            print("✅ Ambient noise adjustment works")
        return True
    except Exception as e:
        print(f"❌ Microphone error: {e}")
        return False

if __name__ == "__main__":
    test_microphone()

# import objc
# print(objc.__version__)
