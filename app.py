import streamlit as st
import openai
from PyPDF2 import PdfReader
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
import re

st.set_page_config(page_title="IA Mantenimiento", layout="wide")
st.title("🔧 Plataforma IA para Mantenimiento")

# -----------------------
# Validar secrets mínimos
# -----------------------
required_secrets = ["OPENAI_API_KEY", "DRIVE_FOLDER_ID", "google"]
missing = [s for s in required_secrets if s not in st.secrets]
if missing:
    st.error(f"Faltan secrets requeridos: {missing}. Añádelos en Settings > Secrets.")
    st.stop()

# -----------------------
# OpenAI
# -----------------------
openai.api_key = st.secrets["OPENAI_API_KEY"]

# -----------------------
# Google Creds & clients
# -----------------------
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = st.secrets["google"]

try:
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    drive_service = build("drive", "v3", credentials=creds, cache_discovery=False)
except Exception as e:
    st.exception("Error al inicializar credenciales de Google. Revisa st.secrets['google'].")
    st.stop()

DRIVE_FOLDER_ID = st.secrets["DRIVE_FOLDER_ID"]

# -----------------------
# Helpers
# -----------------------
def safe_df_from_sheet(spreadsheet_name: str, worksheet_name: str) -> pd.DataFrame:
    """Lee la hoja de Google Sheets y retorna un DataFrame saneado."""
    try:
        ws = client.open(spreadsheet_name).worksheet(worksheet_name)
    except Exception as e:
        st.error(f"No pude abrir '{spreadsheet_name}' -> hoja '{worksheet_name}'. Revisa permisos y nombres.")
        st.stop()
    datos = ws.get_all_values()
    if not datos or len(datos) < 1:
        return pd.DataFrame()
    df = pd.DataFrame(datos[1:], columns=datos[0])
    df = df.fillna("").astype(str)
    return df

def extract_drive_id(url: str) -> str | None:
    """Extrae el id de Drive de varios formatos de links."""
    if not url:
        return None
    url = url.strip()
    # direct uc?id=...
    m = re.search(r"uc\?id=([A-Za-z0-9_-]+)", url)
    if m:
        return m.group(1)
    # /file/d/<id>/
    m = re.search(r"/file/d/([A-Za-z0-9_-]+)", url)
    if m:
        return m.group(1)
    # open?id=...
    m = re.search(r"open\?id=([A-Za-z0-9_-]+)", url)
    if m:
        return m.group(1)
    # if url is just an id
    if re.fullmatch(r"[A-Za-z0-9_-]{10,}", url):
        return url
    return None

def to_public_uc_url(url: str) -> str:
    """Convierte un enlace cualquiera de Drive a https://drive.google.com/uc?id=ID si es posible."""
    drive_id = extract_drive_id(url)
    if drive_id:
        return f"https://drive.google.com/uc?id={drive_id}"
    return url

def is_valid_image_url(url: str) -> bool:
    """Chequeo simple: es URL y no vacío (may be improved)."""
    if not url or url.lower() in ("none", "nan", "nan.0", ""):
        return False
    return url.startswith("http://") or url.startswith("https://")

def upload_file_to_drive(uploaded_file) -> str:
    """
    Sube un archivo a Drive y retorna URL pública tipo uc?id=...
    uploaded_file: Streamlit UploadedFile
    """
    try:
        file_bytes = io.BytesIO(uploaded_file.getvalue())
        mime = uploaded_file.type if uploaded_file.type else "application/octet-stream"
        metadata = {
            "name": uploaded_file.name,
            "parents": [DRIVE_FOLDER_ID]
        }
        media = MediaIoBase
