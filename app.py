import streamlit as st
import openai
from PyPDF2 import PdfReader
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

# ============================
# Configuración de página
# ============================
st.set_page_config(page_title="IA Mantenimiento", layout="wide")
st.title("🔧 Plataforma IA para Mantenimiento")

# ============================
# OpenAI
# ============================
openai.api_key = st.secrets["OPENAI_API_KEY"]

# ============================
# Google Credentials
# ============================
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds_dict = st.secrets["google"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# ============================
# Google Drive
# ============================
drive_service = build('drive', 'v3', credentials=creds)

def subir_imagen_drive(imagen_file):
    """Sube imagen a Google Drive y regresa URL pública"""
    file_metadata = {
        'name': imagen_file.name,
        'parents': [st.secrets["DRIVE_FOLDER_ID"]]
    }
    imagen_bytes = io.BytesIO(imagen_file.getvalue())
    media = MediaIoBaseUpload(imagen_bytes, mimetype=imagen_file.type, resumable=True)
    file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()
    
    imagen_id = file.get('id')
    return f"https://drive.google.com/uc?id={imagen_id}"

# ============================
# Acceso a BD
# ============================
sheet_mtto = client.open("MiBaseMtto").worksheet("Mantenimientos")
sheet_refacciones = client.open("MiBaseMtto").worksheet("Refacciones")

# ============================
# Tabs
# ============================
tab1, tab2, tab3, tab4 = st.tabs(["Chatbot", "Manual", "Mantenimientos", "Refacciones"])

# ======================================================
# TAB CHATBOT
# ======================================================
with tab1:
    st.header("💬 Chat con IA")
    uploaded_file = st.file_uploader("Sube tu manual en PDF", type="pdf")

    if uploaded_file:
        pdf_reader = PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() or ""

        st.success("Texto extraído correctamente")

        question = st.text_input("Escribe tu pregunta:")
        if question:
            with st.spinner("Consultando IA..."):
                prompt = (
                    "Actúa como un ingeniero de mantenimiento experto. "
                    "Responde de forma breve y clara, con pasos prácticos si aplica. "
                    f"Usa el siguiente texto como referencia:\n\n{text[:4000]}\n\nPregunta:\n{question}"
                )

                response = openai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
