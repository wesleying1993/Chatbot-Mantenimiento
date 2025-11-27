import streamlit as st
import openai
from PyPDF2 import PdfReader
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import io
import os

# ===========================
# CONFIGURACIÓN DE LA PÁGINA
# ===========================
st.set_page_config(page_title="IA Mantenimiento", layout="wide")
st.title("🔧 Plataforma IA para Mantenimiento")

# ===========================
# OPENAI
# ===========================
openai.api_key = st.secrets["OPENAI_API_KEY"]

# ===========================
# GOOGLE SHEETS
# ===========================
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

creds_dict = st.secrets["google"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# Abrir documento
sheet = client.open("MiBaseMtto")
sheet_mtto = sheet.worksheet("Mantenimientos")
sheet_refacciones = sheet.worksheet("Refacciones")

# ===========================
# PESTAÑAS
# ===========================
tab1, tab2, tab3, tab4 = st.tabs(["Chatbot", "Manual", "Mantenimientos", "Refacciones"])

# =========================================================
# TAB 1: Chatbot
# =========================================================
with tab1:
    st.header("💬 Chat con IA")
    uploaded_file = st.file_uploader("Sube tu manual en PDF", type="pdf")

    uploaded_bytes = None

    if uploaded_file:
        uploaded_bytes = uploaded_file.read()
        pdf_reader = PdfReader(io.BytesIO(uploaded_bytes))

        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() or ""

        st.success("Texto extraído del PDF con éxito")

        question = st.text_input("Escribe tu pregunta:")
        if question:
            with st.spinner("Consultando IA..."):
                prompt = (
                    "Actúa como un ingeniero de mantenimiento experto. Responde de forma clara y práctica. "
                    f"Referencia técnica:\n\n{text[:4000]}\n\nPregunta del usuario:\n{question}"
                )
                try:
                    response = openai.ChatCompletion.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.2,
                        max_tokens=300
                    )
                    answer = response.choices[0].message.content
                    st.write("**Respuesta:**")
                    st.write(answer)

                except Exception as e:
                    st.error(f"Error al consultar OpenAI: {e}")

# =========================================================
# TAB 2: Manual (descarga)
# =========================================================
with tab2:
    st.header("📘 Manual del equipo")
    if uploaded_bytes:
        st.download_button("Descargar manual", data=uploaded_bytes, file_name="manual.pdf")
    else:
        st.info("Carga un manual en la pestaña Chatbot para verlo aquí.")

# =========================================================
# TAB 3: Mantenimientos
# =========================================================
with tab3:
    st.header("🛠 Mantenimientos Preventivos y Realizados")

    data_mtto = sheet_mtto.get_all_records()

    preventivos = [row for row in data_mtto if row.get("Tipo") == "Preventivo"]
    realizados = [row for row in data_mtto if row.get("Tipo") == "Realizado"]

    st.subheader("📌 Preventivos:")
    st.table(preventivos)

    st.subheader("📍 Realizados:")
    st.table(realizados)

    st.subheader("✚ Agregar mantenimiento")

    col1, col2 = st.columns(2)
    with col1:
        tipo = st.selectbox("Tipo", ["Preventivo", "Realizado"])
        descripcion = st.text_input("Descripción del mantenimiento")

    with col2:
        equipo = st.text_input("Equipo")
        fecha = st.date_input("Fecha")

    if st.button("Guardar en hoja"):
        sheet_mtto.append_row([tipo, descripcion, equipo, str(fecha)])
        st.success("Registro guardado en Google Sheets")

# =========================================================
# TAB 4: Refacciones
# =========================================================
with tab4:
    st.header("🔩 Lista de Refacciones")
    refacciones = sheet_refacciones.get_all_records()

    for ref in refacciones:
        st.write(f"**{ref['Nombre']}** — Cantidad: {ref['Cantidad']}")
        if ref["Imagen_URL"]:
            st.image(ref["Imagen_URL"], width=150)
