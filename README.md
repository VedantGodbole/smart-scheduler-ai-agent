**## Setup Instructions**

**### 1. Virtual Environment Setup**

```bash
# Create virtual environment
python -m venv smart_scheduler_env

# Activate virtual environment
# On Windows:
smart_scheduler_env\Scripts\activate
# On macOS/Linux:
source smart_scheduler_env/bin/activate

# Install dependencies
pip install -r requirements.txt
```

**### 2. Environment Configuration**

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys
```

**### 3. Google Calendar Setup**
**1.** Go to Google Cloud Console
**2.** Create a new project **or** select existing
**3.** Enable Google Calendar API
**4.** Create credentials **(**Service Account**)**
**5.** Download JSON **and** save **as** `credentials**/**google_credentials**.**json`

**### 4. Run Tests**

```bash
# Run all tests
python -m pytest tests/-v

# Run specific test
python -m pytest tests/test_agent.py -v
```

**### 5. Run the Agent**

```bash
python main.py
```
