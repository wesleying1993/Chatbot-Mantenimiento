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
def safe_df_from_sheet(spreadsheet_name, worksheet_name):
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

def extract_drive_id(url):
    """Extrae el id de Drive de varios formatos de links."""
    if not url:
        return None
    url = url.strip()
    m = re.search(r"uc\?id=([A-Za-z0-9_-]+)", url)
    if m:
        return m.group(1)
    m = re.search(r"/file/d/([A-Za-z0-9_-]+)", url)
    if m:
        return m.group(1)
    m = re.search(r"open\?id=([A-Za-z0-9_-]+)", url)
    if m:
        return m.group(1)
    if re.fullmatch(r"[A-Za-z0-9_-]{10,}", url):
        return url
    return None

def to_public_uc_url(url):
    """Convierte un enlace cualquiera de Drive a https://drive.google.com/uc?id=ID si es posible."""
    drive_id = extract_drive_id(url)
    if drive_id:
        return f"https://drive.google.com/uc?id={drive_id}"
    return url

def is_valid_image_url(url):
    """Chequeo simple: es URL y no vacío."""
    if not url or url.lower() in ("none", "nan", "nan.0", ""):
        return False
    return url.startswith("http://") or url.startswith("https://")

def upload_file_to_drive(uploaded_file):
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
        # aquí estaba el posible problema si se corta la línea; la dejamos intacta
        media = MediaIoBaseUpload(file_bytes, mimetype=mime, resumable=True)
        created = drive_service.files().create(
            body=metadata, media_body=media, fields="id", supportsAllDrives=True
        ).execute()
        file_id = created.get("id")
        # hacer público
        drive_service.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader"},
            supportsAllDrives=True
        ).execute()
        return f"https://drive.google.com/uc?id={file_id}"
    except Exception as e:
        st.error(f"No pude subir la imagen a Drive: {e}")
        return ""

# -----------------------
# Config de hojas & nombres
# -----------------------
SPREADSHEET_NAME = "MiBaseMtto"
SHEET_MTT = "Mantenimientos"
SHEET_REF = "Refacciones"

EXPECTED_MTT_COLS = ["Fecha", "Equipo", "Tipo", "Horas", "Notas", "Tecnico", "Imagen_URL"]
EXPECTED_REF_COLS = ["Nombre", "Imagen_URL", "Cantidad", "Locacion"]

# -----------------------
# UI: Tabs
# -----------------------
tab1, tab2, tab3, tab4 = st.tabs(["Chatbot", "Manual", "Mantenimientos", "Refacciones"])

# -----------------------
# TAB 1: Chatbot
# -----------------------
with tab1:
    st.header("💬 Chat IA - Soporte Técnico")
    uploaded_pdf = st.file_uploader("Sube tu manual en PDF (opcional, para contexto)", type="pdf", key="manual_pdf")
    question = st.text_input("Pregunta:", key="question_input")

    if uploaded_pdf and question:
        try:
            uploaded_pdf.seek(0)
            pdf_reader = PdfReader(uploaded_pdf)
            text = "".join([page.extract_text() or "" for page in pdf_reader.pages])
            preview_text = text[:4000]
            prompt = (
                "Actúa como un ingeniero de mantenimiento experto. "
                "Responde de forma breve, con pasos prácticos si aplica. "
                f"Usa el siguiente texto como referencia:\n\n{preview_text}\n\nPregunta:\n{question}"
            )
            with st.spinner("Procesando respuesta..."):
                response = openai.ChatCompletion.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=400
                )
            answer = response["choices"][0]["message"]["content"]
            st.markdown("**Respuesta:**")
            st.success(answer)
        except Exception as e:
            st.error(f"Error al procesar PDF / OpenAI: {e}")

# -----------------------
# TAB 2: Manual (descarga)
# -----------------------
with tab2:
    st.header("📘 Manual")
    if "manual_pdf" in st.session_state and st.session_state["manual_pdf"] is not None:
        pdf_bytes = st.session_state["manual_pdf"].getvalue()
        st.download_button("Descargar PDF subido", data=pdf_bytes, file_name="manual.pdf")
    elif uploaded_pdf:
        uploaded_pdf.seek(0)
        st.download_button("Descargar PDF subido", data=uploaded_pdf.getvalue(), file_name="manual.pdf")
    else:
        st.info("Sube un PDF en la pestaña Chatbot para poder descargarlo desde aquí.")

# -----------------------
# TAB 3: Mantenimientos
# -----------------------
with tab3:
    st.header("📋 Historial de Mantenimiento")

    df = safe_df_from_sheet(SPREADSHEET_NAME, SHEET_MTT)

    if df.empty:
        st.info("La hoja de Mantenimientos está vacía o no existe.")
    else:
        missing_cols = [c for c in EXPECTED_MTT_COLS if c not in df.columns]
        if missing_cols:
            st.warning(f"Faltan columnas en 'Mantenimientos': {missing_cols}. Asegúrate que estén exactamente con esos nombres.")
        df["Imagen_URL"] = df["Imagen_URL"].apply(lambda u: to_public_uc_url(u))
        st.dataframe(df, use_container_width=True)

        st.subheader("📸 Imágenes de evidencia")
        imagenes = []
        for _, row in df.iterrows():
            url = str(row.get("Imagen_URL", "")).strip()
            url = to_public_uc_url(url)
            if is_valid_image_url(url):
                imagenes.append({"url": url, "equipo": row.get("Equipo", "")})

        if not imagenes:
            st.info("No hay imágenes válidas registradas.")
        else:
            per_page = st.selectbox("Imágenes por página", options=[3, 6, 9], index=1)
            total_pages = (len(imagenes) - 1) // per_page + 1
            page = st.number_input("Página", min_value=1, max_value=total_pages, value=1, step=1)
            inicio = (page - 1) * per_page
            fin = inicio + per_page
            cols = st.columns(per_page)
            for i, item in enumerate(imagenes[inicio:fin]):
                try:
                    with cols[i]:
                        st.image(item["url"], use_column_width=True, caption=item["equipo"])
                except Exception as e:
                    st.warning(f"No pude cargar: {item['url']}")

        st.subheader("✍️ Registrar mantenimiento")
        with st.form("registro_mantenimiento", clear_on_submit=True):
            fecha = st.date_input("Fecha")
            equipo = st.text_input("Equipo")
            tipo = st.text_input("Tipo")
            horas = st.text_input("Horas")
            notas = st.text_area("Notas")
            tecnico = st.text_input("Tecnico")
            imagen = st.file_uploader("Evidencia fotográfica (opcional)", type=["jpg", "jpeg", "png"])
            enviar = st.form_submit_button("Guardar")

            if enviar:
                url_imagen = ""
                if imagen:
                    url_imagen = upload_file_to_drive(imagen)
                try:
                    sheet = client.open(SPREADSHEET_NAME).worksheet(SHEET_MTT)
                    sheet.append_row([str(fecha), equipo, tipo, horas, notas, tecnico, url_imagen])
                    st.success("Mantenimiento registrado con éxito.")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"No pude guardar el registro en Google Sheets: {e}")

# -----------------------
# TAB 4: Refacciones
# -----------------------
with tab4:
    st.header("🔩 Refacciones")
    df_r = safe_df_from_sheet(SPREADSHEET_NAME, SHEET_REF)
    if df_r.empty:
        st.info("La hoja de Refacciones está vacía o no existe.")
    else:
        missing_ref = [c for c in EXPECTED_REF_COLS if c not in df_r.columns]
        if missing_ref:
            st.warning(f"Faltan columnas en 'Refacciones': {missing_ref}. Asegúrate que estén exactamente con esos nombres.")

        df_r["Imagen_URL"] = df_r["Imagen_URL"].apply(lambda u: to_public_uc_url(u))
        st.dataframe(df_r, use_container_width=True)

        st.subheader("📸 Imágenes de Refacciones")
        imagenes_r = []
        for _, row in df_r.iterrows():
            url = str(row.get("Imagen_URL", "")).strip()
            url = to_public_uc_url(url)
            if is_valid_image_url(url):
                imagenes_r.append({"url": url, "nombre": row.get("Nombre", "")})

        if not imagenes_r:
            st.info("No hay imágenes válidas en Refacciones.")
        else:
            per_page = st.selectbox("Imágenes por página (Refacciones)", options=[3, 6, 9], index=0, key="per_ref")
            total_pages = (len(imagenes_r) - 1) // per_page + 1
            page = st.number_input("Página (Refacciones)", min_value=1, max_value=total_pages, value=1, step=1, key="page_ref")
            inicio = (page - 1) * per_page
            fin = inicio + per_page
            cols = st.columns(per_page)
            for i, item in enumerate(imagenes_r[inicio:fin]):
                try:
                    with cols[i]:
                        st.image(item["url"], use_column_width=True, caption=item["nombre"])
                except Exception as e:
                    st.warning(f"No pude cargar: {item['url']}")

        st.subheader("✍️ Registrar refacción")
        with st.form("registro_refaccion", clear_on_submit=True):
            nombre = st.text_input("Nombre")
            cantidad = st.text_input("Cantidad")
            locacion = st.text_input("Locación")
            imagen_r = st.file_uploader("Imagen de refacción (opcional)", type=["jpg", "jpeg", "png"], key="ref_img")
            enviar_r = st.form_submit_button("Guardar refacción")

            if enviar_r:
                url_img_r = ""
                if imagen_r:
                    url_img_r = upload_file_to_drive(imagen_r)
                try:
                    sheet_r = client.open(SPREADSHEET_NAME).worksheet(SHEET_REF)
                    sheet_r.append_row([nombre, url_img_r, cantidad, locacion])
                    st.success("Refacción registrada con éxito.")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"No pude guardar la refacción en Google Sheets: {e}")
