from setuptools import setup, find_packages

setup(
    name="smart-scheduler",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "openai>=1.12.0",
        "google-api-python-client>=2.118.0",
        "google-auth-httplib2>=0.2.0",
        "google-auth-oauthlib>=1.2.0",
        "speechrecognition>=3.10.1",
        "pyttsx3>=2.90",
        "pyaudio>=0.2.13",
        "python-dotenv>=1.0.1",
        "pytest>=8.0.0",
        "python-dateutil>=2.8.2",
        "pytz>=2024.1",
    ],
    python_requires=">=3.8",
)
