# --- Advertencia ---
# El comando para correrlo es: streamlit run /Users/wivboost/Desktop/Embeddings_OFF/Front/front_prueba.py


# --- Importamos las librerías necesarias ---

import streamlit as st                # Para crear la interfaz de usuario
import numpy as np                    # Para manejo de arrays y matrices
import pandas as pd                   # Para manejo de datos
import json                           # Para manejo de JSON
import matplotlib.pyplot as plt       # Para visualización de datos
import seaborn as sns                 # Para visualización de datos
from PIL import Image                 # Para manejo de imágenes
import time                           # Para manejo de tiempo
import os                             # Para manejo de archivos y directorios
from dotenv import load_dotenv        # Para cargar variables de entorno desde un archivo .env


# --- Dependencias de Vertex AI ---
import vertexai                                                                 # Para interactuar con Vertex AI
from vertexai import init                                                       # Inicializa Vertex AI con las credenciales y configuración del proyecto
from vertexai.vision_models import MultiModalEmbeddingModel                     # Para trabajar con el modelo de embedding multimodal
from vertexai.vision_models import Image as VMImage                             # Para manejar imágenes en Vertex AI
from vertexai.vision_models import Video, VideoSegmentConfig                    # Para manejar videos y sus segmentos
from google.cloud.aiplatform.matching_engine import MatchingEngineIndexEndpoint # Para conectarse y consultar un endpoint de Vector Search
from google.cloud import storage                                                # Para manejar Google Cloud Storage
import re


# --- Carga variables de entorno ---
load_dotenv()
PROJECT_ID = os.getenv("PROJECT_ID")
INDEX_ENDPOINT_NAME = os.getenv("INDEX_ENDPOINT_NAME")
DEPLOYED_INDEX_ID = os.getenv("DEPLOYED_INDEX_ID")
LOCATION = os.getenv("LOCATION")


# --- Inicializa Vertex AI ---
init(project=PROJECT_ID, location=LOCATION)


# --- Modelos de embedding ---
mm_embedding_model = MultiModalEmbeddingModel.from_pretrained("multimodalembedding@001")



# --- Funciones para embeddings y búsqueda ---

def get_text_embedding(text: str):
    embeddings = mm_embedding_model.get_embeddings(contextual_text=text, dimension=1408)
    return embeddings.text_embedding

def get_image_embedding(image_file, dimension: int = 1408):
    image = VMImage.load_from_file(image_file)
    embedding = mm_embedding_model.get_embeddings(image=image, dimension=dimension)
    return embedding.image_embedding

def find_nearest_neighbors(query_embedding: list, num_neighbors: int = 2017):
    index_endpoint = MatchingEngineIndexEndpoint(index_endpoint_name=INDEX_ENDPOINT_NAME)
    neighbors = index_endpoint.find_neighbors(
        deployed_index_id=DEPLOYED_INDEX_ID,
        queries=[query_embedding],
        num_neighbors=num_neighbors
    )
    return neighbors

def get_public_url_from_gcs(gcs_uri: str) -> str:
    return gcs_uri.replace("gs://", "https://storage.googleapis.com/").replace(" ", "%20")

def display_video_segment_st(video_gcs_uri: str, segment_id: str, interval: int):
    try:
        segment_number = int(segment_id.split('_')[-1])
        start_time = segment_number * interval
        end_time = start_time + interval
        public_url = get_public_url_from_gcs(video_gcs_uri)
        st.markdown(f"**Mostrando segmento:** `{segment_id}` (segundos {start_time}-{end_time})")
        st.video(f"{public_url}#t={start_time},{end_time}")
    except (ValueError, IndexError) as e:
        st.warning(f"No se pudo parsear el ID del segmento '{segment_id}'. Error: {e}")
        



# --- Interfaz de Usuario ---

# --- Logo perfectamente centrado usando columnas de Streamlit ---
col1, col2, col3 = st.columns([1,2,1])
with col2:
    st.image("Front/logo_wivboost.png", width=480)

st.title("🎬 Búsqueda de testigos con Vector Search")
st.write("""
Bienvenido a la búsqueda de logos con Vector Search. 
Puedes buscar solo escribiendo el nombre de la marca, o subiendo una imagen de referencia.
""")

# --- Busqueda por texto ---
text_query = st.text_input("Buscar con texto:", placeholder="Ej: 'Coca Cola'")

st.write("O")

# --- Busqueda por imagen ---
image_query = st.file_uploader("Buscar con una imagen:", type=['png', 'jpg', 'jpeg'])
search_button = st.button("Buscar Videos")


GCS_VIDEO_URI = "gs://vboxioof/Videos/Videos_Segmentados/"  
SEGMENT_INTERVAL_SEC = 4

if search_button:

    if text_query or image_query:
        if image_query is not None:
            st.image(image_query, caption="Imagen de búsqueda", width=250)
            with open("temp_img_st_query.png", "wb") as f:
                f.write(image_query.read())
            image_embedding = get_image_embedding("temp_img_st_query.png")
            search_results = find_nearest_neighbors(image_embedding, 20)

        else:
            text_emb = get_text_embedding(text_query)
            search_results = find_nearest_neighbors(text_emb, 2017)

        if not search_results or not search_results[0]:
            st.info("No se encontraron resultados.")
            st.session_state['video_results'] = []

        else:
            neighbors_sorted = sorted(search_results[0], key=lambda x: x.distance)
            st.session_state['video_results'] = neighbors_sorted

    else:
        st.warning("Por favor, introduce un texto o sube una imagen para buscar.")
        st.session_state['video_results'] = []


# Mostrar resultados si existen en session_state
if 'video_results' in st.session_state and st.session_state['video_results']:

    neighbors_sorted = st.session_state['video_results']
    st.success(f"¡Búsqueda completada! Se encontraron {len(neighbors_sorted)} segmentos.")

    num_to_show = st.slider(
        "Selecciona cuántos segmentos quieres ver:",
        min_value=1,
        max_value=len(neighbors_sorted),
        value=min(5, len(neighbors_sorted)),
        step=1
    )

    for i in range(num_to_show):

        neighbor = neighbors_sorted[i]
        video_segment_id = neighbor.id
        distancia = neighbor.distance
        st.write(f"**ID:** `{video_segment_id}` - **Distancia:** `{distancia:.8f}`")
        match = re.search(r'_(\d+)$', video_segment_id)

        if match:
            segment_index = int(match.group(1))
            video_index = segment_index // 30  # 30 segmentos por video
            segment_in_video = segment_index % 30
            clip_name = f"clip_{video_index}.mp4"

            # Cada segmento dura SEGMENT_INTERVAL_SEC segundos
            start_time_global = segment_index * SEGMENT_INTERVAL_SEC
            end_time_global = start_time_global + SEGMENT_INTERVAL_SEC

            # Offset dentro del clip de 2 minutos
            start_time_clip = segment_in_video * SEGMENT_INTERVAL_SEC
            end_time_clip = start_time_clip + SEGMENT_INTERVAL_SEC
            st.write(f"🔹 Este segmento está en **{clip_name}**, segundos {start_time_clip}-{end_time_clip}.")
            gcs_uri = f"gs://vboxioof/Videos/Videos_Segmentados/{clip_name}"

            display_video_segment_st(
                video_gcs_uri=gcs_uri,
                segment_id=video_segment_id,
                interval=SEGMENT_INTERVAL_SEC
            )

        else:
            st.warning(f"No se pudo extraer el índice de segmento de '{video_segment_id}'")
