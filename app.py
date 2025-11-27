import streamlit as st
import openai
from PyPDF2 import PdfReader
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
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

        with st.spinner("Procesando respuesta..."):
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=300
            )
        st.write("**Respuesta:**")
        st.success(response["choices"][0]["message"]["content"])

# ======================================================
# TAB MANUAL
# ======================================================
with tab2:
    st.header("📘 Manual")
    if uploaded_file:
        st.download_button("Descargar PDF", data=uploaded_file.read(), file_name="manual.pdf")
    else:
        st.info("Sube un PDF en la pestaña Chatbot")

# ======================================================
# TAB MANTENIMIENTOS
# ======================================================
with tab3:
    st.header("📋 Historial de Mantenimiento")

    datos = sheet_mtto.get_all_values()
    df = pd.DataFrame(datos[1:], columns=datos[0])

    st.dataframe(df)

    st.subheader("📸 Imágenes de evidencia:")
    for i, row in df.iterrows():
        if row["Imagen Evidencia"]:
            st.image(row["Imagen Evidencia"], width=200, caption=row["Equipo"])

    st.subheader("✍️ Registrar mantenimiento")

    with st.form("registro_mantenimiento"):
        fecha = st.date_input("Fecha")
        equipo = st.text_input("Equipo")
        descripcion = st.text_area("Descripción")
        responsable = st.text_input("Responsable")
        imagen = st.file_uploader("Evidencia fotográfica", type=["jpg", "jpeg", "png"])

        enviar = st.form_submit_button("Guardar")

        if enviar:
            if imagen:
                url_imagen = subir_imagen_drive(imagen)
            else:
                url_imagen = ""

            sheet_mtto.append_row([str(fecha), equipo, descripcion, responsable, url_imagen])

            st.success("Mantenimiento registrado")
            st.experimental_rerun()

# ======================================================
# TAB REFACCIONES
# ======================================================
with tab4:
    st.header("🔩 Refacciones")

    datos_r = sheet_ref.get_all_values()
    df_r = pd.DataFrame(datos_r[1:], columns=datos_r[0])
    st.dataframe(df_r)

    st.subheader("📸 Imagenes de Refacciones:")
    for i, row in df_r.iterrows():
        if row["Imagen_URL"]:
            st.image(row["Imagen_URL"], width=200, caption=row["Nombre"])
