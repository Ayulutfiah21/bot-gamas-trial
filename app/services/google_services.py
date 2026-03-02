import gspread
import json
import os
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from app.config import CREDS
from google.auth.transport.requests import Request
# ================= GOOGLE SHEETS (Service Account) =================
client = gspread.authorize(CREDS)

# ================= GOOGLE DRIVE =================
token_json = os.getenv("GOOGLE_OAUTH_TOKEN")

if token_json:
    # Railway (pakai environment variable)
    oauth_creds = Credentials.from_authorized_user_info(
        json.loads(token_json)
    )
else:
    # Lokal (pakai file)
    oauth_creds = Credentials.from_authorized_user_file(
        "credentials/token.json"
    )

if oauth_creds.expired and oauth_creds.refresh_token:
    oauth_creds.refresh(Request())

drive = build("drive", "v3", credentials=oauth_creds)