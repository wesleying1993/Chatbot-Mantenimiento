import streamlit as st
from openai import OpenAI
from PyPDF2 import PdfReader
import os

# Configuración
st.set_page_config(page_title="IA chat de Mtto", layout="wide")
st.title("📘 IA chat de Mtto")

# Inicializar cliente OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Subir PDF
uploaded_file = st.file_uploader("Sube tu manual en PDF", type="pdf")

if uploaded_file:
    pdf_reader = PdfReader(uploaded_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()

    st.success("Texto extraído ✅")

    st.subheader("💬 Haz tu pregunta")
    question = st.text_input("Escribe tu pregunta:")

    if question:
        with st.spinner("Consultando IA..."):
            prompt = f"Responde la siguiente pregunta usando el texto del manual:\n\nTexto:\n{text}\n\nPregunta:\n{question}"
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # más rápido y económico
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            st.write("**Respuesta:**", response.choices[0].message.content)
