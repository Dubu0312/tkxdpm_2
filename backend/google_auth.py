"""One-off Google OAuth consent flow.

Run once to turn a downloaded OAuth client secret into a stored token:

    cd backend && python google_auth.py

It opens a browser, asks for permission to manage calendar events, and writes
the token to ``GOOGLE_TOKEN_FILE``. Neither file is ever committed — both live
under ``secrets/``, which is git-ignored.
"""

import sys

from app.config import settings
from app.google_calendar import GoogleApiCalendarClient


def main() -> None:
    from google_auth_oauthlib.flow import InstalledAppFlow

    secret = settings.google_credentials_path
    token = settings.google_token_path

    if not secret.exists():
        print(
            f"Missing OAuth client secret at {secret}.\n"
            "Create an OAuth client (type: Desktop app) in Google Cloud Console, "
            "download the JSON and save it there. See the README.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    flow = InstalledAppFlow.from_client_secrets_file(
        str(secret), GoogleApiCalendarClient.SCOPES
    )
    credentials = flow.run_local_server(port=0)

    token.parent.mkdir(parents=True, exist_ok=True)
    token.write_text(credentials.to_json())
    token.chmod(0o600)
    print(f"Saved OAuth token to {token}. Set GOOGLE_CALENDAR_MODE=google to use it.")


if __name__ == "__main__":
    main()
