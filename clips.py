# --- PASO 1: VERIFICAR/INSTALAR FFMPEG ---

import sys                                # Para interactuar con el intérprete de Python, como salir del script si es necesario.
import subprocess                         # Permite ejecutar comandos del sistema operativo, como instalar paquetes o ejecutar programas externos.            
import os                                 # Para interactuar con el sistema operativo.
import json                               # Permite trabajar con datos en formato JSON.
import functions_framework                # Permite crear y ejecutar funciones como servicios web, útil para Google Cloud Functions.
from google.cloud import storage          # Cliente oficial de Python para interactuar con Google Cloud Storage (subir, descargar y gestionar archivos).


print("Verificando e instalando dependencias...")
try:
    # Verificamos si ffmpeg está disponible
    subprocess.run(["ffmpeg", "-version"], check=True, capture_output=True, text=True)
    print("- ffmpeg ya está instalado.")

except (subprocess.CalledProcessError, FileNotFoundError):
    print("- Intentando instalar ffmpeg...")
    try:
        subprocess.check_call(["apt-get", "-qq", "install", "ffmpeg"])
        print("- ¡ffmpeg instalado correctamente!")

    except (subprocess.CalledProcessError, FileNotFoundError):
        print("ERROR: No se pudo instalar ffmpeg automáticamente. Este script no puede continuar sin él.")
        # Salimos si no se puede instalar
        sys.exit("FFmpeg no está disponible.")



# --- PASO 2: CÓDIGO DEL SCRIPT ---

def get_video_duration(video_path):
    """Obtiene la duración de un video usando ffprobe (parte de ffmpeg)."""

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
        print(f"Error al obtener la duración del video: {e}")
        return None


def dividir_video_con_ffmpeg(ruta_video: str, carpeta_salida: str, duracion_clip_seg: int = 120):
    """
    Divide un video en clips usando llamadas directas a ffmpeg con cortes precisos.
    """
    if not os.path.exists(ruta_video):
        print(f"ERROR: No se encontró el video en la ruta: '{ruta_video}'")
        return

    if not os.path.exists(carpeta_salida):
        print(f"Creando carpeta de salida: '{carpeta_salida}'")
        os.makedirs(carpeta_salida)

    print(f"\nObteniendo duración del video: {ruta_video}")
    total_duration = get_video_duration(ruta_video)
    
    if total_duration is None:
        print("No se pudo procesar el video.")
        return
        
    print(f"Duración total: {total_duration:.2f} segundos.")
    print("\nEmpezando a generar los clips con FFmpeg (modo preciso, puede tardar más)...")
    
    clip_count = 1
    for i in range(0, int(total_duration), duracion_clip_seg):
        start_time = i
        end_time = min(i + duracion_clip_seg, total_duration)
        nombre_clip = f"clip_{clip_count}.mp4"
        ruta_clip_salida = os.path.join(carpeta_salida, nombre_clip)
        
        print(f"  - Creando {nombre_clip} (desde {start_time:.2f}s hasta {end_time:.2f}s)...")
        
        # --- ESTE ES EL COMANDO CORREGIDO PARA PRECISIÓN ---
        # -i [entrada]: Archivo de entrada primero
        # -ss [inicio]: Busca el tiempo de inicio exacto
        # -to [fin]: Corta hasta el tiempo de finalización exacto
        # -c:v libx264 -c:a aac: Volvemos a codificar para asegurar un corte limpio
        command = [
            "ffmpeg",
            "-i", ruta_video,
            "-ss", str(start_time),
            "-to", str(end_time),
            "-c:v", "libx264",
            "-c:a", "aac",
            "-y",
            ruta_clip_salida
        ]
        
        # Ejecutamos el comando, ocultando su salida
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        clip_count += 1

    print("\n¡Proceso de división completado!")
    print(f"Se crearon {clip_count - 1} clips en la carpeta '{carpeta_salida}'.")



# --- PASO 3: EJECUCIÓN ---

if __name__ == "__main__":

    ruta_video_largo = "Copia de Prueba.mp4" 
    carpeta_salida_clips = "/Users/wivboost/Downloads/Borrar"  
    dividir_video_con_ffmpeg(ruta_video_largo, carpeta_salida_clips, 5)