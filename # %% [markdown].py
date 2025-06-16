# %% [markdown]
# # **Importamos las dependencias**

# %%
# --- Para el proceso de datos y visualización ---
import numpy as np
import pandas as pd
import json
import matplotlib.pyplot as plt
import seaborn as sns
pd.options.mode.chained_assignment = None  # default='warn'
from google.cloud import storage



# --- Dependencias de Vertex AI ---
import vertexai                                              # Importa el módulo principal de Vertex AI.
from vertexai import init                                    # Inicializa Vertex AI con las credenciales y configuraciones necesarias.
from vertexai.vision_models import MultiModalEmbeddingModel  # Importa el modelo de embeddings multimodales de Vertex AI para procesar imágenes y videos.
from vertexai.vision_models import Video                     # Clase para manejar archivos de video en Vertex AI.
from vertexai.vision_models import VideoSegmentConfig        # Configuración para segmentar videos al gener
from google.cloud.aiplatform.matching_engine import MatchingEngineIndexEndpoint 


# --- Dependencias para poder visualizar ---
from IPython.display import Video as MVideo                  # Permite mostrar videos directamente en celdas de Jupyter Notebook.
from IPython.display import HTML                             # Permite mostrar contenido HTML en celdas de Jupyter Notebook.
from IPython.display import Image as ImageByte               # Permite mostrar imágenes en el notebook (renombrado como ImageByte para evitar conflictos de nombres).
from IPython.display import display                          # Función general para mostrar objetos en el notebook.
from sklearn.metrics.pairwise import cosine_similarity       # Función para calcular la similitud coseno entre vectores, útil para comparar embeddings.

# %% [markdown]
# # **Configuración del entorno de Vertex**

# %%
# --- Cargamos el modelo de embeddings multimodales ---
mm_embendding_model = MultiModalEmbeddingModel.from_pretrained("multimodalembedding@001")

# %%
# --- Cargamos las credewntiales de Vertex AI ---

PROJECT_ID = "dauntless-drive-462416-q3"
LOCATION = "us-central1"


# --- Inicializamos Vertex AI ---
init(project = PROJECT_ID, location = LOCATION)

# %% [markdown]
# # **Funciones**

# %%
# --- Función para generar embeddings de videos ---

def get_video_embedding(ruta_video: str) -> list: 
    
    """
    Genera un embedding para un video dado.

    Args:
        ruta_video (str): Ruta al archivo de video.

    Returns:
        list: Embedding del video.
    """
    # Cargamos el video desde la ruta proporcionada
    video = Video.load_from_file(ruta_video)
    
    # Genera el embedding del video utilizando el modelo de embeddings multimodales
    embedding = mm_embendding_model.get_embeddings(video = video, 
                                                   video_segment_config = VideoSegmentConfig(interval_sec=4) # Configura el segmento del video para generar embeddings cada 4 segundos.
                                                  )
    
    return [video_emb.embedding for video_emb in embedding.video_embeddings]  # Retorna una lista de embeddings para cada segmento del video.


# --- Función para generar embeddings de texto ---

def get_text_embedding(text: str) -> list:
    """Genera un embedding para un texto dado."""
    print(f"Generando embedding para el texto: '{text}'")
    embeddings = mm_embendding_model.get_embeddings(
        contextual_text=text,
    )
    return embeddings.text_embedding



def find_nearest_neighbors(query_embedding: list, num_neighbors: int = 8):
    """Busca los N vecinos más cercanos a un embedding de consulta."""
    print("Conectando al Index Endpoint...")
    index_endpoint = MatchingEngineIndexEndpoint(index_endpoint_name=INDEX_ENDPOINT_NAME)
    
    print(f"Buscando los {num_neighbors} videos más similares...")
    neighbors = index_endpoint.find_neighbors(
        deployed_index_id=DEPLOYED_INDEX_ID,
        queries=[query_embedding],
        num_neighbors=num_neighbors
    )
    return neighbors

def display_video_segment(video_gcs_uri: str, segment_id: str, interval: int):
    """Muestra un reproductor de video HTML que apunta a un segmento específico."""
    try:
        # Extraemos el número del segmento del ID. Ej: "VIDEOYAGO_segment_5" -> 5
        segment_number = int(segment_id.split('_')[-1])
        start_time = segment_number * interval
        end_time = start_time + interval
        
        # Convertimos la URI de gs:// a una URL pública de https://
        public_url = video_gcs_uri.replace("gs://", "https://storage.googleapis.com/")
        
        # Creamos el código HTML para el video, apuntando al tiempo de inicio
        video_html = f"""
        <p>Mostrando segmento: <b>{segment_id}</b> (segundos {start_time}-{end_time})</p>
        <video width="640" controls>
            <source src="{public_url}#t={start_time},{end_time}" type="video/mp4">
            Tu navegador no soporta la etiqueta de video.
        </video>
        """
        display(HTML(video_html))
        
    except (ValueError, IndexError) as e:
        print(f"No se pudo parsear el ID del segmento '{segment_id}'. Error: {e}")




# --- Convierte una URI de Google Cloud Storage a una URL pública accesible por HTTP ---

def get_public_url_from_gcs(gcs_uri: str) -> str:
    """
    Convierte una URI de Google Cloud Storage (gs://bucket/archivo) a una URL pública HTTP.

    Args:
        gcs_uri (str): URI de Google Cloud Storage.

    Returns:
        str: URL pública accesible desde el navegador.
    """
    return gcs_uri.replace("gs://", "https://storage.googleapis.com/").replace(
        " ", "%20"
    )



# --- Muestra un video almacenado en Google Cloud Storage en el notebook ---

def display_video_from_gcs(gcs_uri: str) -> None:
    """
    Muestra un video almacenado en Google Cloud Storage directamente en el notebook.

    Args:
        gcs_uri (str): URI de Google Cloud Storage del video.
    """
    public_url = get_public_url_from_gcs(gcs_uri)
    display(
        HTML(
            f"""
            <video width="480" controls>
                <source src="{public_url}" type="video/mp4">
                Tu navegador no soporta la reproducción de video.
            </video>
            """
        )
    )


# --- Función para imprimir videos similares basados en embeddings ---

def print_similar_videos(query_emb: list[float], data_frame: pd.DataFrame):
    """
    Calcula la similitud (producto punto) entre un embedding de consulta y los embeddings de videos almacenados en un DataFrame.
    Muestra los videos más similares y despliega el video más relevante en el notebook.

    Args:
        query_emb (list[float]): Embedding de consulta (por ejemplo, generado a partir de un video o texto).
        data_frame (pd.DataFrame): DataFrame que contiene al menos las columnas 'video_embeddings', 'file_name' y 'gcs_path'.

    Funcionamiento:
        - Calcula el producto punto entre el embedding de consulta y cada embedding de video en el DataFrame.
        - Añade una columna 'score' con los resultados de similitud.
        - Ordena el DataFrame por 'score' de mayor a menor.
        - Imprime los nombres de los archivos y sus scores más altos.
        - Muestra el video más similar directamente en el notebook.
    """
    # Obtiene la columna de embeddings de video
    video_embs = data_frame["video_embeddings"]

    # Calcula el producto punto entre cada embedding y el de consulta
    scores = [np.dot(eval(video_emb), query_emb) for video_emb in video_embs]
    data_frame["score"] = scores

    # Ordena por score descendente
    data_frame = data_frame.sort_values(by="score", ascending=False)

    # Imprime los resultados principales
    print(data_frame.head()[["score", "file_name"]])

    # Obtiene la URL GCS del video más similar
    url = data_frame.iloc[0]["gcs_path"]

    # Muestra el video en el notebook
    display_video_from_gcs(url)



# --- Función para guardar embeddings en Google Cloud Storage como JSONL ---

def guardar_embeddings_en_gcs(
    project_id: str,
    bucket_name: str,
    blob_name: str,
    ids: list[str],
    embeddings: list[list[float]]
):
    """
    Convierte una lista de IDs y embeddings al formato JSONL y lo sube a GCS.

    Args:
        project_id (str): Tu proyecto de Google Cloud.
        bucket_name (str): El nombre del bucket de destino.
        blob_name (str): La ruta y nombre del archivo a crear en el bucket.
        ids (list[str]): Lista de IDs únicos para cada embedding.
        embeddings (list[list[float]]): La lista de vectores de embedding.
    """
    print(f"Conectando al bucket '{bucket_name}'...")
    storage_client = storage.Client(project=project_id)
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    print(f"Escribiendo {len(ids)} embeddings en el archivo en memoria...")
    
    # Usamos un context manager para escribir directamente al archivo en GCS
    with blob.open("w") as f:
        for i, embedding in zip(ids, embeddings):
            # Creamos el diccionario para la línea actual
            data_point = {"id": i, "embedding": embedding}
            # Lo convertimos a un string JSON y escribimos la línea en el archivo
            f.write(json.dumps(data_point) + "\n")

    print(f"¡Éxito! Archivo '{blob_name}' subido correctamente a 'gs://{bucket_name}/{blob_name}'.")



# %% [markdown]
# # **Generamos los embeddings**

# %%
ruta_video = "gs://canalesparaprueba/VIDEOYAGO.mp4" # Ruta al video

# Generamos el embedding del video
video_embedding = get_video_embedding(ruta_video)

# %%
len(video_embedding)

# %% [markdown]
# # **Carga a Vector Search**

# %%
INDEX_ENDPOINT_NAME = "projects/144706985230/locations/us-central1/indexEndpoints/7120122841151832064"
DEPLOYED_INDEX_ID = "embeddings_video_yago_prue_1749587612895"
BUCKET_NAME = "canalesparaprueba" #  Aquí era otro bucket, me equivoqué xd
DESTINATION_BLOB_NAME = "embeddings/video_embeddings_yago.json" 


# --- GENERACIÓN DE IDs ---
ids_de_embeddings = [f"VIDEOYAGO_segment_{i}" for i in range(len(video_embedding))]


if len(ids_de_embeddings) != len(video_embedding):
        raise ValueError("La cantidad de IDs no coincide con la cantidad de embeddings.")
        
guardar_embeddings_en_gcs(
    project_id=PROJECT_ID,
    bucket_name=BUCKET_NAME,
    blob_name=DESTINATION_BLOB_NAME,
    ids=ids_de_embeddings,
    embeddings=video_embedding
)



# %% [markdown]
# # **Query a los embeddings**

# %%
# La ruta original de tu video. La necesitamos para poder mostrar el fragmento.
GCS_VIDEO_URI = "gs://borrar_valerio/VIDEOYAGO.mp4"
SEGMENT_INTERVAL_SEC = 4 # El intervalo en segundos que usaste para segmentar el video

# --- INICIALIZACIÓN Y MODELOS ---
# Asumo que vertexai.init() ya se ejecutó.
# Creamos una instancia del modelo de embedding para usarlo en la función de texto.



# --- EJECUCIÓN DE LA BÚSQUEDA ---
if __name__ == '__main__':
    
    # ------------------------------------------------------------------
    # AQUÍ PONES TU CONSULTA EN LENGUAJE NATURAL
    texto_de_busqueda = "Volt"
    # ------------------------------------------------------------------
    
    # 1. Obtenemos el embedding del texto de búsqueda
    query_emb = get_text_embedding(texto_de_busqueda)
    
    # 2. Buscamos en Vector Search usando el embedding del texto
    search_results = find_nearest_neighbors(query_emb)
    
    # 3. Mostramos los resultados
    print("\n--- RESULTADOS DE LA BÚSQUEDA ---")
    
    if not search_results or not search_results[0]:
        print("No se encontraron resultados.")
    else:
        for neighbor in search_results[0]:
            video_segment_id = neighbor.id
            distancia = neighbor.distance
            print(f"\nEncontrado: [ID: {video_segment_id}] - [Distancia: {distancia:.4f}]")
            
            # Mostramos el fragmento de video correspondiente
            display_video_segment(
                video_gcs_uri=GCS_VIDEO_URI,
                segment_id=video_segment_id,
                interval=SEGMENT_INTERVAL_SEC
            )


