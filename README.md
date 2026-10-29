# VoiceDesk AI — AI Voice Receptionist

VoiceDesk AI is a production-ready AI Voice Receptionist designed for small businesses (clinics, salons, consultancies, law offices, and local services). It handles incoming voice calls, answers customer FAQs naturally, checks appointment slot availability, books appointments into a local SQLite database, and synchronizes confirmed bookings with Google Calendar via OAuth 2.0.

---

## 1. Project Overview and Architecture

```
my-agent/
├── data/                         # Persistent local data (SQLite DB, OAuth tokens)
│   ├── appointments.db           # SQLite database storing bookings
│   └── google_token.json         # Google OAuth refresh & access tokens (Git-ignored)
├── src/
│   ├── agent.py                  # LiveKit Agent entrypoint (STT, LLM, TTS, Voice Pipeline)
│   ├── config.py                 # Central configuration and environment loader
│   ├── database/
│   │   └── appointments_db.py    # Parameterized SQLite database repository
│   ├── prompts/
│   │   └── receptionist_prompt.py # Professional voice persona instructions & rules
│   ├── scripts/
│   │   ├── authorize_google.py   # CLI tool to authorize Google Calendar OAuth
│   │   └── view_appointments.py  # CLI tool to inspect stored appointments
│   ├── services/
│   │   ├── appointment_service.py# Business validation, conflicts, and booking logic
│   │   └── calendar_service.py   # Google Calendar API integration & OAuth flow
│   ├── tools/
│   │   ├── business_info.py      # Voice tools for hours, location, services, policies
│   │   └── calendar.py           # Voice tools for checking slots, booking, and cancelling
│   └── utils/
│       └── logging.py            # Safe, structured logging
├── tests/
│   ├── test_agent.py             # LiveKit turn-level and conversational tests
│   ├── test_appointment_service.py # Validation and conflict detection tests
│   ├── test_calendar_service.py  # Mocked Google Calendar API tests
│   └── test_database.py          # SQLite CRUD and schema tests
├── .env.example                  # Environment variable template
├── .env.local                    # Local environment variables (Git-ignored)
├── livekit.toml                  # LiveKit project configuration
└── pyproject.toml                # Dependencies and project metadata
```

### Technology Stack
* **Language & Runtime**: Python 3.10+ (tested on Python 3.14)
* **Voice Agent Infrastructure**: LiveKit Agents SDK 1.8 (`livekit-agents`)
* **Speech-to-Text (STT)**: Deepgram Nova-3 (`deepgram/nova-3`)
* **Large Language Model (LLM)**: Google Gemma (`google/gemma-4-31b-it`)
* **Text-to-Speech (TTS)**: Cartesia Sonic-3 (`cartesia/sonic-3`)
* **Database**: SQLite 3 (parameterized queries, zero-maintenance local storage)
* **Calendar Integration**: Google Calendar API v3 via OAuth 2.0
* **Package & Environment Manager**: `uv`

---

## 2. Prerequisites

* **Operating System**: Linux (Ubuntu 22.04+ recommended), macOS, or Windows WSL2
* **Python**: Python 3.10 to 3.14
* **uv**: Fast Python package installer and runner
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
* **LiveKit CLI (`lk`)**:
  ```bash
  curl -sSL https://get.livekit.io/cli | bash
  ```

---

## 3. Virtual Environment Setup

Navigate to your project directory:
```bash
cd ~/bharadwaj/projects/voicedesk-ai/my-agent
```

If you wish to manually activate the virtual environment:
```bash
source .venv/bin/activate
```
*(Note: With `uv`, you can directly run commands using `uv run <command>`, which automatically uses the `.venv` environment).*

---

## 4. Install Dependencies

Install all core and development dependencies using `uv`:
```bash
cd ~/bharadwaj/projects/voicedesk-ai/my-agent
uv sync
```

---

## 5. Configure Environment Variables (`.env.local`)

Copy the template to create your local `.env.local` file:
```bash
cd ~/bharadwaj/projects/voicedesk-ai/my-agent
cp .env.example .env.local
```

Edit `.env.local` with your credentials:
```ini
# LiveKit Cloud Configuration (required)
LIVEKIT_URL=wss://voicedesk-ai-XXXX.livekit.cloud
LIVEKIT_API_KEY=your_api_key_here
LIVEKIT_API_SECRET=your_api_secret_here

# AI Models (defaults to ultra-fast LiveKit Cloud Inference models)
LLM_MODEL=google/gemma-4-31b-it
STT_MODEL=deepgram/nova-3
TTS_MODEL=cartesia/sonic-3

# Business Persona
BUSINESS_NAME=VoiceDesk
BUSINESS_TYPE=General Services & Appointments
BUSINESS_HOURS="Monday through Saturday from 9:00 AM to 6:00 PM. Closed on Sundays."
BUSINESS_LOCATION="123 Innovation Boulevard, Suite 200"
BUSINESS_SERVICES="General Consultation, Service Appointment, Follow-up Visit"
BUSINESS_POLICIES="Please arrive five minutes prior to your scheduled time. Cancellations should be made at least two hours in advance."
BUSINESS_TIMEZONE=UTC

# SQLite Database Storage
DATABASE_PATH=data/appointments.db

# Google Calendar OAuth 2.0 (Phase 3)
GOOGLE_CLIENT_ID=your_google_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
GOOGLE_CALENDAR_ID=primary
GOOGLE_TOKEN_FILE=data/google_token.json
```

---

## 6. How to Run the Voice Agent

### Option A: Interactive Text Debugger (Recommended for fast testing)
Run turns and see tool calls, responses, and events without audio devices:
```bash
cd ~/bharadwaj/projects/voicedesk-ai/my-agent
lk agent debugger start
lk agent debugger say "What are your business hours?"
lk agent debugger say "I would like to book a consultation tomorrow at 2 PM. My name is Bharadwaj, phone 555-123-4567"
lk agent debugger say "Yes, please book it."
lk agent debugger stop
```

### Option B: Interactive Voice Console (Speaking through microphone)
Connects directly to your laptop mic or USB headset:
```bash
cd ~/bharadwaj/projects/voicedesk-ai/my-agent

# List detected audio devices
lk agent console --list-devices

# Run using default audio devices:
lk agent console

# Or specify your USB headset (e.g. BH900 PRO):
lk agent console --input-device "BH900" --output-device "BH900"
```

### Option C: LiveKit Development Mode (Connecting to LiveKit Cloud Room)
```bash
cd ~/bharadwaj/projects/voicedesk-ai/my-agent
lk agent dev
```

---

## 7. Initialize and Inspect SQLite Database

The database is initialized automatically on first run at `data/appointments.db`.

To inspect saved appointments:
```bash
cd ~/bharadwaj/projects/voicedesk-ai/my-agent
uv run python src/scripts/view_appointments.py
```

Or query directly using the SQLite CLI or Python:
```bash
uv run python -c "
import sqlite3
conn = sqlite3.connect('data/appointments.db')
for row in conn.execute('SELECT id, customer_name, appointment_date, appointment_time, status FROM appointments'):
    print(row)
"
```

---

## 8. Google Cloud Setup: Creating a Project

1. Open the [Google Cloud Console](https://console.cloud.google.com/).
2. Click the project dropdown at the top and click **New Project**.
3. Name your project `VoiceDesk-AI` and click **Create**.
4. Make sure your new project is selected in the top bar.

---

## 9. Enable Google Calendar API

1. In the Google Cloud Console, navigate to **APIs & Services** > **Library**.
2. In the search bar, type `Google Calendar API`.
3. Select **Google Calendar API** from the results and click **Enable**.

---

## 10. Configure OAuth Consent Screen & Credentials

### Step A: Configure Consent Screen
1. Navigate to **APIs & Services** > **OAuth consent screen**.
2. Select **External** (or Internal if using Google Workspace) and click **Create**.
3. Fill in:
   * **App name**: `VoiceDesk AI`
   * **User support email**: your email
   * **Developer contact email**: your email
4. Click **Save and Continue**.
5. In **Scopes**, click **Add or Remove Scopes**, find `Google Calendar API`, and select:
   * `.../auth/calendar.events` (View and edit events)
6. In **Test Users**, add your personal Google email address so you can authorize the app while in Testing status.
7. Click **Save and Continue**.

### Step B: Create OAuth 2.0 Client ID
1. Navigate to **APIs & Services** > **Credentials**.
2. Click **+ Create Credentials** > **OAuth client ID**.
3. Select Application type: **Web application** (or **Desktop app**).
4. Name: `VoiceDesk Calendar Client`.
5. Under **Authorized redirect URIs**, add:
   * `http://localhost:8000/auth/google/callback`
   * `http://localhost:8080/`
6. Click **Create**.
7. Copy your **Client ID** and **Client Secret** into your `.env.local` file:
   ```ini
   GOOGLE_CLIENT_ID=your_copied_client_id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your_copied_client_secret
   ```

---

## 11. Authorize the Business Owner's Calendar

Once you have added `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` to `.env.local`, run the authorization utility:

```bash
cd ~/bharadwaj/projects/voicedesk-ai/my-agent
uv run python src/scripts/authorize_google.py
```

* A browser window will open asking you to sign in with your Google Account.
* Grant calendar event permissions.
* The utility will automatically save the refresh and access tokens to `data/google_token.json`.
* All future appointments booked by the voice agent will now automatically create verified events on your Google Calendar!

---

## 12. Running Tests

Run the full automated test suite (SQLite, Appointment Service, Google Calendar Mock, Agent Turn Tests):

```bash
cd ~/bharadwaj/projects/voicedesk-ai/my-agent
uv run pytest -v
```

Run code formatting and lint checks:
```bash
uv run ruff check
uv run ruff format --check
```

---

## 13. Common Troubleshooting Steps

| Issue | Cause | Solution |
|---|---|---|
| `ALSA lib: Invalid CTL hw:0` | PortAudio querying NVIDIA HDMI audio as capture | Use `--input-device default` or pass your USB headset name e.g. `--input-device "BH900"` in `lk agent console`. |
| `Google Calendar check: not connected` | `GOOGLE_CLIENT_ID` missing or `data/google_token.json` not created | Run `uv run python src/scripts/authorize_google.py` after adding client credentials to `.env.local`. |
| `Appointment saved as PENDING` | Google Calendar is either unconfigured or returned an error | Normal Phase 2 behavior. Appointments are safely recorded in SQLite. Once Google Calendar is authorized, bookings sync as `CONFIRMED`. |
| `ValidationError: in the past` | Caller specified a past date | The agent automatically detects dates earlier than today and asks the caller to select a future date. |
| `LiveKit Inference timeout` | Temporary internet or gateway lag | The LiveKit Agent SDK automatically retries transient network errors with exponential backoff. |
