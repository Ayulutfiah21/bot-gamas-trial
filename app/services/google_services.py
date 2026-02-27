import gspread
from oauth2client.service_account import ServiceAccountCredentials
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.config import SERVICE_JSON, OAUTH_TOKEN

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name(
    SERVICE_JSON,
    scope
)

client = gspread.authorize(creds)

oauth_creds = Credentials.from_authorized_user_file(OAUTH_TOKEN)
drive = build("drive", "v3", credentials=oauth_creds)