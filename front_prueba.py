import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np

# IMPORTANTE:
# Aquí deberías importar las funciones reales del backend.
# Por ejemplo:
# from CargaEmbeddings import get_text_embedding, find_nearest_neighbors, get_image_embedding

# CONSTANTES para mostrar el video
GCS_VIDEO_URI = "gs://borrar_valerio/VIDEOYAGO.mp4"
SEGMENT_INTERVAL_SEC = 4

def show_video_segment(video_gcs_uri: str, segment_id: str, interval: int):
    """
    Muestra un segmento de video usando HTML embebido en Streamlit.
    """
    try:
        # Ej: "VIDEOYAGO_segment_1" -> extrae el número de segmento
        segment_number = int(segment_id.split('_')[-1])
        start_time = segment_number * interval
        end_time = start_time + interval
        public_url = video_gcs_uri.replace("gs://", "https://storage.googleapis.com/")
        video_html = f"""
        <p>Mostrando segmento: <b>{segment_id}</b> (segundos {start_time}-{end_time})</p>
        <video width="640" controls>
            <source src="{public_url}#t={start_time},{end_time}" type="video/mp4">
            Tu navegador no soporta la etiqueta de video.
        </video>
        """
        components.html(video_html, height=400, scrolling=True)
    except Exception as e:
        st.error(f"Error al mostrar el video: {e}")

# ----- Funciones simuladas de backend (reemplázalas por las reales) -----

def get_text_embedding(text: str) -> list:
    st.write(f"Simulando generación de embedding para: '{text}'")
    # Retorna un embedding dummy (en tu implementación se llamará al modelo)
    return [0.1, 0.2, 0.3]

def find_nearest_neighbors(query_embedding: list, num_neighbors: int = 8):
    st.write("Simulando búsqueda de vecinos...")
    # Creamos una clase dummy para simular el objeto neighbor
    class Neighbor:
        def __init__(self, id, distance):
            self.id = id
            self.distance = distance

    # Dummy: siempre retorna un vecino para la demostración
    dummy_neighbor = Neighbor("VIDEOYAGO_segment_1", 0.12345678)
    return [[dummy_neighbor]]  # Se devuelve una lista anidada

def get_image_embedding(image_bytes: bytes) -> list:
    st.write("Simulando generación de embedding para la imagen...")
    return [0.4, 0.5, 0.6]

# ----- Frontend Streamlit -----
st.title("Búsqueda de Videos por Embeddings")

# Selección del tipo de búsqueda
option = st.radio("Selecciona el tipo de búsqueda:", ("Consulta en texto", "Subir imagen"))

if option == "Consulta en texto":
    query_text = st.text_input("Escribe tu consulta en lenguaje natural:")
    if st.button("Buscar", key="text_search"):
        if query_text:
            query_emb = get_text_embedding(query_text)
            search_results = find_nearest_neighbors(query_emb)
            if not search_results or not search_results[0]:
                st.write("No se encontraron resultados.")
            else:
                for neighbor in search_results[0]:
                    st.write(f"Encontrado: [ID: {neighbor.id}] - [Distancia: {neighbor.distance:.8f}]")
                    show_video_segment(GCS_VIDEO_URI, neighbor.id, SEGMENT_INTERVAL_SEC)
        else:
            st.warning("Por favor, ingresa una consulta.")

else:
    uploaded_file = st.file_uploader("Sube una imagen", type=["jpg", "jpeg", "png"])
    if uploaded_file is not None:
        image_bytes = uploaded_file.read()
        query_emb = get_image_embedding(image_bytes)
        search_results = find_nearest_neighbors(query_emb)
        if not search_results or not search_results[0]:
            st.write("No se encontraron resultados.")
        else:
            for neighbor in search_results[0]:
                st.write(f"Encontrado: [ID: {neighbor.id}] - [Distancia: {neighbor.distance:.8f}]")
                show_video_segment(GCS_VIDEO_URI, neighbor.id, SEGMENT_INTERVAL_SEC)