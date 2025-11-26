import streamlit as st
import openai
from PyPDF2 import PdfReader
import os

# Configuración de la página
st.set_page_config(page_title="IA Mantenimiento", layout="wide")
st.title("🔧 Plataforma IA para Mantenimiento")

# Configurar API Key
openai.api_key = os.getenv("OPENAI_API_KEY")

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
    st.write("Aquí puedes mostrar el manual completo o secciones importantes.")
    st.info("Sube el PDF en la pestaña Chatbot para verlo aquí.")
    if uploaded_file:
        st.download_button("Descargar Manual", data=uploaded_file.read(), file_name="manual.pdf")

# ===========================
# TAB 3: Mantenimientos
# ===========================
with tab3:
    st.header("🛠 Mantenimientos Preventivos")
    st.write("Lista de mantenimientos programados:")
    st.table([
        {"Fecha": "2025-12-01", "Actividad": "Cambio de filtros"},
        {"Fecha": "2026-01-15", "Actividad": "Lubricación general"},
        {"Fecha": "2026-02-10", "Actividad": "Revisión eléctrica"}
    ])

    st.subheader("Historial de mantenimientos realizados:")
    st.table([
        {"Fecha": "2025-10-20", "Actividad": "Revisión de válvulas"},
        {"Fecha": "2025-09-05", "Actividad": "Cambio de aceite"}
    ])

# ===========================
# TAB 4: Refacciones
# ===========================
with tab4:
    st.header("🔩 Lista de Refacciones")
    st.image("https://via.placeholder.com/150", caption="Filtro de aceite")
    st.image("https://via.placeholder.com/150", caption="Bomba hidráulica")
    st.image("https://via.placeholder.com/150", caption="Sensor de presión")
