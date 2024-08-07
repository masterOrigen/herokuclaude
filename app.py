import streamlit as st
import anthropic
from dotenv import load_dotenv
import os
from PyPDF2 import PdfReader
import PyPDF2
import io
import traceback
import streamlit.components.v1 as components
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

# Configuración de FastAPI y CORS
app = FastAPI()

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite todas las origenes, ajusta esto en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Agregar SessionMiddleware
app.add_middleware(SessionMiddleware, secret_key="tu_clave_secreta_aqui")

# Cargar variables de entorno
load_dotenv()

# Configurar el cliente de Anthropic usando la API key del archivo .env
try:
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
except Exception as e:
    st.error(f"Error al inicializar el cliente de Anthropic: {str(e)}")
    st.stop()

def main():
    st.header("Claude Sonnet - GPT MEDIOS")

    # Inicializar los historiales de chat y estados en la sesión si no existen
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'file_chat_history' not in st.session_state:
        st.session_state.file_chat_history = []
    if 'file_content' not in st.session_state:
        st.session_state.file_content = ""
    if 'file_uploaded' not in st.session_state:
        st.session_state.file_uploaded = False

    def get_claude_response(prompt, is_general=True, context=""):
        if is_general:
            system_prompt = ("Eres un asistente AI altamente preciso y confiable. "
                             "Proporciona respuestas extremadamente detalladas, extensas y precisas basadas en tu conocimiento general. "
                             "Utiliza todo el espacio disponible para ofrecer la respuesta más completa posible. "
                             "Si no tienes suficiente información para responder con certeza, indícalo claramente. "
                             "Evita especulaciones y céntrate en hechos verificables.")
            full_prompt = prompt
        else:
            system_prompt = ("Eres un asistente AI altamente preciso y confiable. "
                             "Proporciona respuestas extremadamente detalladas, extensas y precisas basadas en la información disponible en el archivo PDF. "
                             "Utiliza todo el espacio disponible para ofrecer la respuesta más completa posible. "
                             "Si no tienes suficiente información para responder con certeza, indícalo claramente. "
                             "Evita especulaciones y céntrate en hechos verificables del documento proporcionado.")
            full_prompt = f"Contexto del archivo PDF:\n\n{context}\n\nPregunta del usuario: {prompt}\n\nPor favor, responde a la pregunta basándote en el contenido del archivo PDF proporcionado. Sé lo más detallado y extenso posible en tu respuesta."
        
        try:
            message = client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=4090,
                temperature=0,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": full_prompt}
                ]
            )
            return message.content[0].text
        except Exception as e:
            st.error(f"Error al procesar la pregunta: {str(e)}")
            st.error(f"Traceback: {traceback.format_exc()}")
            return "Ha ocurrido un error inesperado. Por favor, inténtalo de nuevo o contacta al soporte técnico."

    def on_general_question_submit():
        if st.session_state.user_question:
            response = get_claude_response(st.session_state.user_question, is_general=True)
            st.session_state.chat_history.append((st.session_state.user_question, response))
            st.session_state.user_question = ""

    def on_file_question_submit():
        if st.session_state.file_question and st.session_state.file_content:
            context = st.session_state.file_content
            response = get_claude_response(st.session_state.file_question, is_general=False, context=context)
            st.session_state.file_chat_history.append((st.session_state.file_question, response))
            st.rerun()

    # Mensaje de advertencia para usuarios de Chrome
    components.html(
        """
        <script>
        if (navigator.userAgent.indexOf("Chrome") != -1) {
            document.write('<div style="color: orange; padding: 10px; border: 1px solid orange; margin: 10px 0;">Si experimenta problemas al subir archivos en Chrome, por favor intente con Firefox o Edge.</div>');
        }
        </script>
        """,
        height=50
    )

    # Crear pestañas
    tab1, tab2 = st.tabs(["Chat General", "Chat con PDF"])

    with tab1:
        st.header("Preguntas Generales")

        # Mostrar el historial de chat general
        for q, a in st.session_state.chat_history:
            st.subheader("Pregunta:")
            st.write(q)
            st.subheader("Respuesta:")
            st.write(a)
            st.markdown("---")

        # Área para nueva pregunta general
        st.text_area("Haga su nueva pregunta aquí:", key="user_question", height=100)
        st.button("Enviar Pregunta", key="general_submit", on_click=on_general_question_submit)

    with tab2:
        st.header("Chat con PDF")

        # Configurar el límite de tamaño del archivo
        MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

        # Subida de archivos
        uploaded_file = st.file_uploader("Elija un archivo PDF", type=["pdf"], key="pdf_uploader")
        
        if uploaded_file is not None:
            file_size = len(uploaded_file.getvalue())
            if file_size > MAX_FILE_SIZE:
                st.error(f"El archivo es demasiado grande. Por favor, suba un archivo de menos de 5 MB. Tamaño actual: {file_size / 1024 / 1024:.2f} MB")
            else:
                try:
                    # Leer el contenido del archivo en memoria
                    file_bytes = uploaded_file.getvalue()
                    
                    # Usar BytesIO para crear un objeto de archivo en memoria
                    file_stream = io.BytesIO(file_bytes)
                    
                    # Intentar leer el PDF
                    pdf_reader = PdfReader(file_stream)
                    file_content = ""
                    for page in pdf_reader.pages:
                        file_content += page.extract_text() + "\n"

                    # Guardar el contenido y actualizar el estado
                    st.session_state.file_content = file_content
                    st.session_state.file_uploaded = True
                    st.success("Archivo PDF subido y procesado exitosamente.")
                    
                    # Mostrar información sobre el PDF
                    st.info(f"Número de páginas: {len(pdf_reader.pages)}")
                    st.info(f"Tamaño del archivo: {file_size / 1024:.2f} KB")
                    
                except Exception as e:
                    st.error("Error al procesar el archivo PDF.")
                    st.error(f"Detalles del error: {str(e)}")
                    st.error("Traceback completo:")
                    st.code(traceback.format_exc())
                    st.info("Por favor, asegúrese de que el archivo es un PDF válido y no está dañado.")
                    st.session_state.file_uploaded = False
                    st.session_state.file_content = ""

        # Área para preguntas sobre el archivo
        if st.session_state.file_uploaded:
            # Mostrar el historial de chat del archivo
            for q, a in st.session_state.file_chat_history:
                st.subheader("Pregunta sobre el archivo:")
                st.write(q)
                st.subheader("Respuesta:")
                st.write(a)
                st.markdown("---")

            # Área para nueva pregunta sobre el archivo
            st.text_area("Haga una nueva pregunta sobre el archivo PDF:", key="file_question", height=100)
            if st.button("Enviar Pregunta sobre el PDF", key="file_submit"):
                on_file_question_submit()

        else:
            st.info("Por favor, suba un archivo PDF válido para hacer preguntas sobre él.")

    # Agregar un footer con información de depuración
    st.markdown("---")
    st.write("Información de depuración:")
    st.write(f"Versión de Streamlit: {st.__version__}")
    st.write(f"Versión de PyPDF2: {PyPDF2.__version__}")

# Configurar los encabezados de respuesta
@app.middleware("http")
async def add_custom_headers(request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["X-Frame-Options"] = "ALLOW-FROM *"
    return response

if __name__ == "__main__":
    main()
