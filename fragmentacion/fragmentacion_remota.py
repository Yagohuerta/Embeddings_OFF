#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import subprocess
from google.cloud import storage
import tempfile
import logging

def fragmentar_video(
    gcs_bucket_entrada: str,
    ruta_video_gcs: str,
    gcs_bucket_salida: str,
    carpeta_destino_gcs: str,
    duracion_segmento: int
):
    """
    Fragmenta un video desde GCS en segmentos de X segundos y sube los fragmentos a otro bucket GCS.
    
    Args:
        gcs_bucket_entrada: Bucket GCS donde está el video original
        ruta_video_gcs: Ruta completa al video en GCS (ej: 'videos/originales/mivideo.mp4')
        gcs_bucket_salida: Bucket GCS de destino para los fragmentos
        carpeta_destino_gcs: Carpeta dentro del bucket de destino
        duracion_segmento: Duración de cada segmento en segundos
    """
    # Configurar logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Crear cliente de GCS
    storage_client = storage.Client()
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        try:
            # 1. Descargar el video desde GCS
            logger.info(f"Descargando video desde gs://{gcs_bucket_entrada}/{ruta_video_gcs}...")
            bucket_entrada = storage_client.bucket(gcs_bucket_entrada)
            blob_video = bucket_entrada.blob(ruta_video_gcs)
            
            nombre_video = os.path.basename(ruta_video_gcs)
            ruta_local_video = os.path.join(tmp_dir, nombre_video)
            blob_video.download_to_filename(ruta_local_video)
            logger.info(f"Video descargado temporalmente a {ruta_local_video}")
            
            # 2. Fragmentar el video
            nombre_base = os.path.splitext(nombre_video)[0]
            extension = os.path.splitext(nombre_video)[1].lower()
            formato_salida = "mp4" if extension == ".mp4" else "mkv"
            
            output_pattern = os.path.join(tmp_dir, f"{nombre_base}_segment_%03d.{formato_salida}")
            
            cmd = [
                "ffmpeg",
                "-i", ruta_local_video,
                "-c:v", "libx264",
                "-x264-params", f"keyint={duracion_segmento*30}:min-keyint={duracion_segmento*30}:force-cfr=1:scenecut=0",
                "-force_key_frames", f"expr:gte(t,n_forced*{duracion_segmento})",
                "-c:a", "aac",
                "-strict", "experimental",
                "-f", "segment",
                "-segment_time", str(duracion_segmento),
                "-segment_format", formato_salida,
                "-reset_timestamps", "1",
                "-avoid_negative_ts", "make_zero",
                "-flags", "+global_header",
                output_pattern
            ]
            
            logger.info(f"Fragmentando video en segmentos de {duracion_segmento} segundos...")
            subprocess.run(cmd, check=True, capture_output=True)
            
            # 3. Obtener lista de fragmentos generados
            fragmentos = sorted([
                f for f in os.listdir(tmp_dir)
                if f.startswith(f"{nombre_base}_segment_") and f.endswith(f".{formato_salida}")
            ])
            
            if not fragmentos:
                raise ValueError("No se generaron fragmentos. Verifica el video de entrada.")
            
            logger.info(f"Generados {len(fragmentos)} fragmentos temporales")
            
            # 4. Subir fragmentos a GCS
            bucket_salida = storage_client.bucket(gcs_bucket_salida)
            logger.info(f"Subiendo fragmentos a gs://{gcs_bucket_salida}/{carpeta_destino_gcs}/")
            
            for frag in fragmentos:
                ruta_local_frag = os.path.join(tmp_dir, frag)
                blob_dest = f"{carpeta_destino_gcs}/{frag}"
                
                # Configurar metadata para los fragmentos
                metadata = {
                    'original_video': ruta_video_gcs,
                    'segment_duration': str(duracion_segmento),
                    'segment_number': frag.split('_')[-1].split('.')[0]
                }
                
                blob = bucket_salida.blob(blob_dest)
                blob.metadata = metadata
                blob.upload_from_filename(ruta_local_frag)
                logger.info(f"Subido: gs://{gcs_bucket_salida}/{blob_dest}")
                
                # Eliminar fragmento local
                os.remove(ruta_local_frag)
            
            logger.info("¡Proceso completado exitosamente!")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Error en ffmpeg: {e.stderr.decode('utf-8')}")
            raise
        except Exception as e:
            logger.error(f"Error inesperado: {str(e)}")
            raise
        finally:
            # Limpiar archivo original descargado si existe
            if os.path.exists(ruta_local_video):
                os.remove(ruta_local_video)

# Ejemplo de uso
if __name__ == "__main__":
    fragmentar_video(
        gcs_bucket_entrada="vm-prueba",
        ruta_video_gcs="final_copa_oro/TUDN/2025-07-06 17-06-44.mkv",
        gcs_bucket_salida="vm-prueba",
        carpeta_destino_gcs="videos/nuevos2",
        duracion_segmento=16
    )