import os
import subprocess
import functions_framework
from google.cloud import storage

# --- CONFIGURACIÓN ---

# ¡IMPORTANTE! Define aquí el bucket donde se guardarán los clips procesados.
OUTPUT_BUCKET_NAME = "vboxioof" # Reemplaza con tu bucket si es necesario.

# Nombre de la "carpeta" dentro del bucket de salida donde se guardarán los clips.
CLIP_FOLDER_IN_BUCKET = "Videos_Segmentados"

# --- FIN DE LA CONFIGURACIÓN ---


# Inicializar el cliente de Storage fuera de la función para optimizar y reutilizar la conexión.
storage_client = storage.Client()

def get_video_duration(video_path: str) -> float | None:
    """
    Obtiene la duración de un video en segundos usando ffprobe (parte de ffmpeg).
    Retorna la duración como un número flotante o None si hay un error.
    """
    command = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path
    ]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        return float(result.stdout)
    except Exception as e:
        print(f"Error al obtener la duración del video con ffprobe: {e}")
        return None

# Este decorador mágico convierte esta función en un servicio que responde a eventos de GCP.
@functions_framework.cloud_event
def split_video_pipeline(cloud_event):
    """
    Cloud Function que se activa con la subida de un video a GCS,
    lo descarga, lo divide en clips precisos y los sube a otro destino en GCS.
    """
    # --- 1. Extraer información del archivo que activó el evento ---
    event_data = cloud_event.data
    source_bucket_name = event_data["bucket"]
    source_blob_name = event_data["name"]
    
    print(f"INFO: Evento detectado para el archivo: gs://{source_bucket_name}/{source_blob_name}")

    # --- 2. Preparar rutas y cliente de GCS ---
    source_bucket = storage_client.bucket(source_bucket_name)
    source_blob = source_bucket.blob(source_blob_name)
    output_bucket = storage_client.bucket(OUTPUT_BUCKET_NAME)

    # Las Cloud Functions solo tienen permiso de escritura en la carpeta /tmp
    temp_folder = "/tmp"
    temp_video_path = os.path.join(temp_folder, os.path.basename(source_blob_name))
    temp_output_folder = os.path.join(temp_folder, "clips_de_salida")

    # Creamos la carpeta temporal para los clips si no existe.
    if not os.path.exists(temp_output_folder):
        os.makedirs(temp_output_folder)

    try:
        # --- 3. Descargar el video de GCS a la carpeta /tmp ---
        print(f"INFO: Descargando video a ruta temporal: {temp_video_path}")
        source_blob.download_to_filename(temp_video_path)
        
        # --- 4. Obtener duración y dividir el video con FFmpeg ---
        total_duration = get_video_duration(temp_video_path)
        if total_duration is None:
            raise RuntimeError("No se pudo obtener la duración del video, abortando.")
            
        print(f"INFO: Duración total: {total_duration:.2f}s. Empezando a generar clips...")
        
        clip_duration_sec = 120  # Clips de 2 minutos
        for i in range(0, int(total_duration), clip_duration_sec):
            start_time = i
            end_time = min(i + clip_duration_sec, total_duration)
            clip_count = (i // clip_duration_sec) + 1
            
            base_name = os.path.splitext(os.path.basename(source_blob_name))[0]
            clip_name = f"{base_name}_clip_{clip_count}.mp4"
            temp_clip_path = os.path.join(temp_output_folder, clip_name)
            
            print(f"  - Creando {clip_name} (de {start_time:.2f}s a {end_time:.2f}s)...")
            
            # Comando FFmpeg para cortes precisos (más lento pero exacto)
            command = [
                "ffmpeg",
                "-i", temp_video_path,
                "-ss", str(start_time),
                "-to", str(end_time),
                "-c:v", "libx264",
                "-c:a", "aac",
                "-y",  # Sobrescribe el archivo de salida si existe
                temp_clip_path
            ]
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # --- 5. Subir los clips generados de vuelta a GCS ---
        print(f"\nINFO: Subiendo clips a gs://{OUTPUT_BUCKET_NAME}/{CLIPS_FOLDER_IN_BUCKET}/")
        
        for clip_filename in os.listdir(temp_output_folder):
            local_clip_path = os.path.join(temp_output_folder, clip_filename)
            destination_blob_name = f"{CLIPS_FOLDER_IN_BUCKET}/{clip_filename}"
            
            blob = output_bucket.blob(destination_blob_name)
            print(f"  - Subiendo {clip_filename}...")
            blob.upload_from_filename(local_clip_path)

    except Exception as e:
        print(f"ERROR: Ocurrió un error durante el procesamiento: {e}")
    finally:
        # --- 6. Limpiar todos los archivos temporales ---
        print("INFO: Realizando limpieza de archivos temporales...")
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)
        if os.path.exists(temp_output_folder):
            for clip_filename in os.listdir(temp_output_folder):
                os.remove(os.path.join(temp_output_folder, clip_filename))
            os.rmdir(temp_output_folder)
        print("INFO: Limpieza completada.")

    return "OK"