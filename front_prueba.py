import streamlit as st
import numpy as np
import pandas as pd
import json
import matplotlib.pyplot as plt
import seaborn as sns
from PIL import Image
import time


# --- Para manejar las variables de entorno ---
import os
from dotenv import load_dotenv


# --- Desactiva las advertencias de asignaciones encadenadas en pandas para evitar mensajes de warning al modificar DataFrames.
pd.options.mode.chained_assignment = None  # default='warn'


# --- Dependencias de Vertex AI ---
import vertexai                                              # Importa el módulo principal de Vertex AI.
from vertexai import init                                    # Inicializa Vertex AI con las credenciales y configuraciones necesarias.
from vertexai.vision_models import MultiModalEmbeddingModel  # Importa el modelo de embeddings multimodales de Vertex AI para procesar imágenes y videos.
from vertexai.vision_models import Video                     # Clase para manejar archivos de video en Vertex AI.
from vertexai.vision_models import VideoSegmentConfig        # Configuración para segmentar videos al gener


# --- Para conectarse y consultar un endpoint de búsqueda vectorial (Vector Search) en Vertex AI.
from google.cloud.aiplatform.matching_engine import MatchingEngineIndexEndpoint 

# --- Para acceder a los buckets de Google Cloud Storage y manejar archivos.
from google.cloud import storage


# --- Simulación de la Función de Búsqueda ---
# En un caso real, aquí llamarías a tu backend de VectorSearch.
# Esta función simulada devuelve una lista de URLs de video de ejemplo.
def perform_vector_search(query_text=None, query_image=None):
    """
    Simula una búsqueda en VectorSearch.
    Devuelve una lista de URLs de video.
    """
    # Simula un tiempo de espera, como si estuviera procesando la búsqueda
    with st.spinner('Buscando en la base de datos de vectores...'):
        time.sleep(2)

    # Simula la obtención de una cantidad variable de resultados
    num_results = np.random.randint(0, 50)
    
    # Lista de videos de ejemplo para mostrar
    sample_videos = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com/watch?v=3JZ_D3ELwOQ",
        "https://www.youtube.com/watch?v=L_LUpnjgPso",
        "https://www.youtube.com/watch?v=tV_gYgfwC-w",
        "https://www.youtube.com/watch?v=fNFzfwLM72c"
    ] * 10 # Multiplicamos para tener suficientes videos para el ejemplo

    # Devuelve una sublista aleatoria de los videos
    return sample_videos[:num_results]

# --- Interfaz de Usuario con Streamlit ---

# Título de la aplicación
st.title("🎬 Búsqueda de Videos con Vector Search")

# Mensaje de bienvenida
st.write("""
Bienvenido a la búsqueda de videos impulsada por IA. 
Puedes buscar usando lenguaje natural (texto) o subiendo una imagen de referencia.
""")

# --- Entradas del Usuario ---

# Campo para la búsqueda con texto
text_query = st.text_input("Buscar con texto:", placeholder="Ej: 'un atardecer en la playa'")

# Campo para subir una imagen
st.write("O") # Separador visual
image_query = st.file_uploader("Buscar con una imagen:", type=['png', 'jpg', 'jpeg'])

# Botón para enviar la consulta
search_button = st.button("Buscar Videos")

# --- Lógica de Búsqueda y Visualización de Resultados ---

if search_button:
    results = []
    # Validar que al menos una de las dos opciones (texto o imagen) tenga contenido
    if text_query or image_query:
        # Si se sube una imagen, mostrarla
        if image_query is not None:
            st.image(image_query, caption="Imagen de búsqueda", width=250)
        
        # Llamar a la función de búsqueda (simulada)
        # En un caso real, pasarías el texto o los bytes de la imagen a tu backend.
        video_results = perform_vector_search(query_text=text_query, query_image=image_query)

        # Guardar los resultados en el estado de la sesión para que persistan
        st.session_state['video_results'] = video_results
    else:
        st.warning("Por favor, introduce un texto o sube una imagen para buscar.")
        # Limpiar resultados anteriores si los hubiera
        if 'video_results' in st.session_state:
            del st.session_state['video_results']


# --- Mostrar Resultados si existen ---

# Comprobar si hay resultados en el estado de la sesión
if 'video_results' in st.session_state:
    video_results = st.session_state['video_results']
    
    st.markdown("---") # Separador horizontal
    
    if len(video_results) > 0:
        st.success(f"¡Búsqueda completada! Se encontraron {len(video_results)} videos.")

        # Barra deslizable para seleccionar cuántos videos mostrar
        num_to_show = st.slider(
            "Selecciona cuántos videos quieres ver:",
            min_value=1,
            max_value=len(video_results),
            value=min(5, len(video_results)),  # Valor por defecto: 5 o el total si es menor
            step=1
        )

        # Mostrar los videos seleccionados
        st.subheader(f"Mostrando los primeros {num_to_show} videos:")
        for i in range(num_to_show):
            st.video(video_results[i])
    else:
        st.info("No se encontraron videos que coincidan con tu búsqueda.")
