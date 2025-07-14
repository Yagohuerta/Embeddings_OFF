#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import subprocess
from google.cloud import storage
import tempfile


#fragmentar video localmente y subir a GCP
def fragmentar_y_subir_video_gcp(
    ruta_video_local: str,
    gcs_bucket_salida: str,
    carpeta_destino_gcs: str,
    duracion_segmento: int
):
    """
    Fragmenta un video local en segmentos de exactamente X segundos y los sube a GCP,
    compatible con MP4 y MKV, manteniendo la máxima calidad posible.
    
    Args:
        ruta_video_local: Ruta al archivo de video a fragmentar (MP4 o MKV)
        gcs_bucket_salida: Nombre del bucket GCS de destino
        carpeta_destino_gcs: Carpeta dentro del bucket donde se guardarán los segmentos
        duracion_segmento: Duración exacta de cada segmento en segundos
    """
    # Crear una carpeta temporal para los fragmentos
    with tempfile.TemporaryDirectory() as carpeta_tmp:
        nombre_base = os.path.splitext(os.path.basename(ruta_video_local))[0]
        extension = os.path.splitext(ruta_video_local)[1].lower()
        
        # Determinar formato de salida basado en la entrada
        formato_salida = "mp4" if extension == ".mp4" else "mkv"
        output_pattern = os.path.join(carpeta_tmp, f"{nombre_base}_segment_%03d.{formato_salida}")
        
        # Comando de ffmpeg optimizado para segmentación precisa
        cmd = [
            "ffmpeg",
            "-i", ruta_video_local,
            "-c:v", "libx264",  # Recodificar video para asegurar keyframes exactos
            "-x264-params", f"keyint={duracion_segmento*30}:min-keyint={duracion_segmento*30}:force-cfr=1:scenecut=0",
            "-force_key_frames", f"expr:gte(t,n_forced*{duracion_segmento})",
            "-c:a", "aac",  # Recodificar audio para sincronización perfecta
            "-strict", "experimental",
            "-f", "segment",
            "-segment_time", str(duracion_segmento),
            "-segment_format", formato_salida,
            "-reset_timestamps", "1",
            "-avoid_negative_ts", "make_zero",
            "-flags", "+global_header",
            output_pattern
        ]
        
        print(f"Fragmentando video con ffmpeg en segmentos exactos de {duracion_segmento} segundos...")
        print("Comando ejecutado:", " ".join(cmd))
        
        try:
            subprocess.run(cmd, check=True)
            
            # Obtener lista de fragmentos generados
            fragmentos = sorted([
                f for f in os.listdir(carpeta_tmp)
                if f.startswith(f"{nombre_base}_segment_") and f.endswith(f".{formato_salida}")
            ])
            
            print(f"¡Fragmentación completada! {len(fragmentos)} segmentos generados temporalmente.")
            
            # Verificar duración de cada fragmento
            if fragmentos:
                print("\nVerificando duración de los segmentos...")
                for i, fragmento in enumerate(fragmentos[:-1]):  # El último puede ser más corto
                    ruta_fragmento = os.path.join(carpeta_tmp, fragmento)
                    cmd_duracion = [
                        "ffprobe",
                        "-v", "error",
                        "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1",
                        ruta_fragmento
                    ]
                    resultado = subprocess.run(cmd_duracion, capture_output=True, text=True)
                    duracion_real = float(resultado.stdout.strip())
                    print(f"Segmento {i+1}: {duracion_real:.2f}s (Diferencia: {abs(duracion_real-duracion_segmento):.2f}s)")
            
            # Subir los fragmentos al bucket de GCS
            storage_client = storage.Client()
            bucket_out = storage_client.bucket(gcs_bucket_salida)
            print(f"\nSubiendo {len(fragmentos)} fragmentos a gs://{gcs_bucket_salida}/{carpeta_destino_gcs}/ ...")
            
            for frag in fragmentos:
                local_path = os.path.join(carpeta_tmp, frag)
                blob_dest = f"{carpeta_destino_gcs}/{frag}"
                bucket_out.blob(blob_dest).upload_from_filename(local_path)
                print(f"  ✅ Subido: gs://{gcs_bucket_salida}/{blob_dest}")
                os.remove(local_path)  # Elimina el fragmento local después de subirlo
            
            print("\n¡Listo! Todos los fragmentos subidos a GCS y eliminados localmente.")
            
        except subprocess.CalledProcessError as e:
            print(f"Error al fragmentar el video: {e}")
            print("Asegúrate de que FFmpeg está instalado y accesible en tu PATH.")
        except Exception as e:
            print(f"Error inesperado: {e}")

# Ejemplo de uso:
fragmentar_y_subir_video_gcp(
    ruta_video_local="/Users/wivboost/Downloads/fran.mkv",
    gcs_bucket_salida="vm-prueba",
    carpeta_destino_gcs="videos/nuevos",
    duracion_segmento=16
)