import streamlit as st
from openai import OpenAI
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
client_openai = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

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
    
    # hacer pública
    drive_service.permissions().create(
        fileId=imagen_id,
        body={'type': 'anyone', 'role': 'reader'}
    ).execute()

    return f"https://drive.google.com/uc?id={imagen_id}"

# ============================
# Acceso a BD
# ============================
sheet_mtto = client.open("MiBaseMtto").worksheet("Mantenimientos")
sheet_ref = client.open("MiBaseMtto").worksheet("Refacciones")

# ============================
# Tabs
# ============================
tab1, tab2, tab3, tab4 = st.tabs(["Chatbot", "Manual", "Mantenimientos", "Refacciones"])

# ======================================================
# TAB CHATBOT
# ======================================================
with tab1:
    st.header("💬 Chat IA - Soporte Técnico")

    uploaded_file = st.file_uploader("Sube tu manual en PDF", type="pdf")
    question = st.text_input("Pregunta:")

    if uploaded_file and question:
        pdf_reader = PdfReader(uploaded_file)
        text = "".join([page.extract_text() or "" for page in pdf_reader.pages])

        prompt = (
            "Actúa como un ingeniero de mantenimiento experto. "
            "Responde de forma breve, con pasos prácticos si aplica. "
            f"Usa el siguiente texto como referencia:\n\n{text[:4000]}\n\nPregunta:\n{question}"
        )

        with st.spinner("Procesando..."):
            response = client_openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=300
            )
        st.write("**Respuesta:**", response["choices"][0]["message"]["content"])


# ======================================================
# TAB MANTENIMIENTOS
# ======================================================
with tab3:
    st.subheader("📋 Historial de Mantenimiento (arriba)")
    data = sheet_mtto.get_all_values()
    st.write(data)

    st.subheader("✍️ Registrar Mantenimiento (abajo)")

    with st.form("registro_mtto"):
        col1, col2 = st.columns(2)

        with col1:
            fecha = st.date_input("Fecha de mantenimiento")
            equipo = st.text_input("Equipo")
            descripcion = st.text_area("Descripción")

        with col2:
            responsable = st.text_input("Responsable")
            imagen = st.file_uploader("Foto evidencia", type=["jpg", "jpeg", "png"])

        submit = st.form_submit_button("Guardar")

        if submit:
            if imagen:
                url_imagen = subir_imagen_drive(imagen)
            else:
                url_imagen = ""

            sheet_mtto.append_row([str(fecha), equipo, descripcion, responsable, url_imagen])

            st.success("Registro guardado correctamente")
            st.experimental_rerun()

