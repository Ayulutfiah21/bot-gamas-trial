import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_DIR = os.path.join(BASE_DIR, "credentials")

SERVICE_JSON = os.path.join(CREDENTIALS_DIR, "service.json")
OAUTH_TOKEN = os.path.join(CREDENTIALS_DIR, "token.json")

DRIVE_ROOT_DATA = os.getenv("DRIVE_ROOT_DATA")
DRIVE_ROOT_FOTO = os.getenv("DRIVE_ROOT_FOTO")
USER_MANAGEMENT_ID = os.getenv("USER_MANAGEMENT_ID")

BULAN_ID = {
    1:"JANUARI",2:"FEBRUARI",3:"MARET",4:"APRIL",
    5:"MEI",6:"JUNI",7:"JULI",8:"AGUSTUS",
    9:"SEPTEMBER",10:"OKTOBER",11:"NOVEMBER",12:"DESEMBER"
}

STO_MAPPING = {
    "BBU": {"sheet":"GAMAS BAU BAU","mitra":"FMP BAU BAU"},
    "WNC": {"sheet":"GAMAS BAU BAU","mitra":"FMP WANCI"},
    "UNH": {"sheet":"FMP UNAAHA","mitra":"FMP UNAAHA"}
}

KET_DEFAULT = [
    "GAMAS BESAR",
    "GAMAS KECIL",
    "INFRA CARE",
    "LAINNYA"
]