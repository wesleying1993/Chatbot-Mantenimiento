import streamlit as st
import openai
from PyPDF2 import PdfReader
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

# Configuración de la página
st.set_page_config(page_title="IA Mantenimiento", layout="wide")
st.title("🔧 Plataforma IA para Mantenimiento")

# Configurar API Key OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Conexión con Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Si usas Streamlit Cloud con Secrets:
creds_dict = st.secrets["google"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

# Si usas local:
# creds = ServiceAccountCredentials.from_json_keyfile_name("credenciales.json", scope)

client = gspread.authorize(creds)

# Abrir hojas
sheet_mtto = client.open("MiBaseMtto").worksheet("Mantenimientos")
sheet_refacciones = client.open("MiBaseMtto").worksheet("Refacciones")

# Crear pestañas
tab1, tab2, tab3, tab4 = st.tabs(["Chatbot", "Manual", "Mantenimientos", "Refacciones"])

# ===========================
# TAB 1: Chatbot
# ===========================
with tab1:
    st.header("💬 Chat con IA")
    uploaded_file = st.file_uploader("Sube tu manual en PDF", type="pdf")

    if uploaded_file:
        pdf_reader = PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() or ""

        st.success("Texto extraído ✅")

        question = st.text_input("Escribe tu pregunta:")
        if question:
            with st.spinner("Consultando IA..."):
                prompt = (
                    "Actúa como un ingeniero de mantenimiento experto. "
                    "Responde de forma breve y clara, con pasos prácticos si aplica. "
                    f"Usa el siguiente texto como referencia:\n\n{text[:4000]}\n\nPregunta:\n{question}"
                )
                try:
                    response = openai.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.2,
                        max_tokens=300
                    )
                    st.write("**Respuesta:**", response.choices[0].message.content)
                except Exception as e:
                    st.error(f"Error al consultar OpenAI: {e}")

# ===========================
# TAB 2: Manual
# ===========================
with tab2:
    st.header("📘 Manual del equipo")
    st.info("Sube el PDF en la pestaña Chatbot para verlo aquí.")
    if uploaded_file:
        st.download_button("Descargar Manual", data=uploaded_file.read(), file_name="manual.pdf")

# ===========================
# TAB 3: Mantenimientos
# ===========================
with tab3:
    st.header("🛠 Mantenimientos Preventivos y Realizados")
    st.subheader("Preventivos:")
    preventivos = [row for row in sheet_mtto.get_all_records() if row["Tipo"] == "Preventivo"]
    st.table(preventivos)

    st.subheader("Realizados:")
    realizados = [row for row in sheet_mtto.get_all_records() if row["Tipo"] == "Realizado"]
    st.table(realizados)

# ===========================
# TAB 4: Refacciones
# ===========================
with tab4:
    st.header("🔩 Lista de Refacciones")
    refacciones = sheet_refacciones.get_all_records()
    for ref in refacciones:
        st.image(ref["Imagen_URL"], caption=f"{ref['Nombre']} (Cantidad: {ref['Cantidad']})")
