"""CLI Script to authorize Google Calendar OAuth 2.0 for VoiceDesk AI.

Run this script to connect your Google Calendar account:
    uv run python src/scripts/authorize_google.py

Or if you prefer manual copy-paste of the authorization URL/code:
    uv run python src/scripts/authorize_google.py --manual
"""

from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import urlparse

# Add src to python path if run directly
src_dir = Path(__file__).parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from config import (  # noqa: E402
    GOOGLE_CALENDAR_ID,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
    GOOGLE_TOKEN_FILE,
)
from services.calendar_service import (  # noqa: E402
    CALENDAR_SCOPES,
    GoogleCalendarService,
)


def main() -> None:
    print("=" * 70)
    print(" VoiceDesk AI — Google Calendar Authorization Utility")
    print("=" * 70)

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        print("\n[ERROR] Missing Google OAuth credentials!")
        print(
            "Please configure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env.local"
        )
        print("\nFollow these steps:")
        print("1. Go to Google Cloud Console: https://console.cloud.google.com")
        print("2. Create a project and enable 'Google Calendar API'")
        print("3. Configure OAuth Consent Screen (External/Testing)")
        print("4. Create an OAuth 2.0 Client ID (Web Application or Desktop App)")
        print(f"5. Add Authorized Redirect URI: {GOOGLE_REDIRECT_URI}")
        print("6. Copy Client ID and Secret to .env.local")
        sys.exit(1)

    cal_service = GoogleCalendarService()
    if cal_service.is_connected():
        print("\n[SUCCESS] Google Calendar is ALREADY authorized and connected!")
        print(f"Token file: {GOOGLE_TOKEN_FILE}")
        print("Testing calendar connection...")
        try:
            _is_free, msg = cal_service.check_calendar_slot("2030-01-01", "12:00")
            print(f"Calendar check test: {msg}")
        except Exception as e:
            print(f"Warning during test call: {e}")
        return

    # Parse port from configured redirect URI
    parsed_uri = urlparse(GOOGLE_REDIRECT_URI)
    port = parsed_uri.port or 8080

    client_config = {
        "installed": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [
                GOOGLE_REDIRECT_URI,
                f"http://localhost:{port}/",
                "http://localhost:8080/",
            ],
        }
    }

    is_manual = "--manual" in sys.argv

    if is_manual:
        print("\n--- Manual Authorization Mode ---")
        from google_auth_oauthlib.flow import Flow

        flow = Flow.from_client_config(
            client_config,
            scopes=CALENDAR_SCOPES,
            redirect_uri=GOOGLE_REDIRECT_URI,
        )
        auth_url, _ = flow.authorization_url(access_type="offline", prompt="consent")
        print("\n1. Open this URL in your web browser:")
        print(f"\n{auth_url}\n")
        print("2. Sign in with your Google Account.")
        print("3. If you see 'Google hasn't verified this app':")
        print("   - Click 'Advanced'")
        print("   - Click 'Go to VoiceDesk AI (unsafe)'")
        print("4. Check the box to allow calendar permissions and click 'Continue'.")
        print(
            "5. After you click 'Continue', Google will redirect your browser to a page."
        )
        print(
            "   The page may say 'Site can't be reached' or 'Unable to connect' — THAT IS COMPLETELY NORMAL!"
        )
        print("   Just copy the ENTIRE URL from your browser's address bar at the top.")
        print("   (It starts with: http://localhost:8080/?state=...&code=...)\n")

        try:
            user_input = input("Paste the copied address bar URL here: ").strip()
        except KeyboardInterrupt:
            print("\nAuthorization cancelled.")
            sys.exit(1)

        if not user_input:
            print("\n[ERROR] No input provided.")
            sys.exit(1)

        try:
            if user_input.startswith("http://") or user_input.startswith("https://"):
                flow.fetch_token(authorization_response=user_input)
            else:
                flow.fetch_token(code=user_input)
            cal_service._save_credentials(flow.credentials)
            print("\n[SUCCESS] Google Calendar authorized successfully!")
            print(f"Credentials saved securely to: {GOOGLE_TOKEN_FILE}")
            print(f"Connected Calendar ID: {GOOGLE_CALENDAR_ID}")
        except Exception as e:
            print(f"\n[ERROR] Failed to exchange token: {e}")
            sys.exit(1)
        return

    # Default Automatic Browser Mode
    print("\nStarting automatic OAuth authorization flow...")
    print(f"Local callback port: {port}")
    print("-" * 70)
    print("INSTRUCTIONS FOR YOUR BROWSER:")
    print("1. Your browser will open the Google Sign-in page automatically.")
    print(
        "   (If it doesn't open, copy and paste the URL shown below into your browser)."
    )
    print("2. Sign in with your Google account.")
    print("3. When you see 'Google hasn't verified this app':")
    print("   -> Click 'Advanced' (small link at bottom left)")
    print("   -> Click 'Go to VoiceDesk AI (unsafe)'")
    print(
        "4. Check the checkbox for 'See, edit, share, and permanently delete all the calendars...'"
    )
    print("5. Click 'Continue'.")
    print("-" * 70)
    print(
        ">> The script is now waiting for you to complete these steps in your browser."
    )
    print(">> DO NOT press Ctrl+C while signing in!")
    print("-" * 70)

    from google_auth_oauthlib.flow import InstalledAppFlow

    try:
        flow = InstalledAppFlow.from_client_config(
            client_config, scopes=CALENDAR_SCOPES
        )
        creds = flow.run_local_server(
            port=port,
            prompt="consent",
            authorization_prompt_message="\nPlease visit this URL if browser did not open:\n{url}\n",
        )
        cal_service._save_credentials(creds)
        print("\n[SUCCESS] Google Calendar authorized successfully!")
        print(f"Credentials saved securely to: {GOOGLE_TOKEN_FILE}")
        print(f"Connected Calendar ID: {GOOGLE_CALENDAR_ID}")
    except KeyboardInterrupt:
        print("\n\n[NOTICE] Authorization was interrupted by Ctrl+C.")
        print(
            "Tip: If the browser didn't redirect or you prefer manual copy-paste, run:"
        )
        print("    uv run python src/scripts/authorize_google.py --manual")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Authorization failed: {e}")
        print("Tip: You can also try manual mode:")
        print("    uv run python src/scripts/authorize_google.py --manual")
        sys.exit(1)


if __name__ == "__main__":
    main()
