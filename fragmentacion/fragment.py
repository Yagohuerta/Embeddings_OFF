#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#fragmentar video localmente
import os
import subprocess

def fragmentacion_local(
    ruta_video_local: str,
    carpeta_salida: str,
    duracion_segmento: int
):
    """
    Fragmenta un video local en segmentos de exactamente X segundos usando ffmpeg,
    compatible con MP4 y MKV, manteniendo la máxima calidad posible.
    
    Args:
        ruta_video_local: Ruta al archivo de video a fragmentar (MP4 o MKV)
        carpeta_salida: Carpeta donde se guardarán los segmentos
        duracion_segmento: Duración exacta de cada segmento en segundos
    """
    if not os.path.exists(carpeta_salida):
        os.makedirs(carpeta_salida)
    
    nombre_base = os.path.splitext(os.path.basename(ruta_video_local))[0]
    extension = os.path.splitext(ruta_video_local)[1].lower()
    
    # Determinar formato de salida basado en la entrada
    formato_salida = "mp4" if extension == ".mp4" else "mkv"
    output_pattern = os.path.join(carpeta_salida, f"{nombre_base}_segment_%03d.{formato_salida}")
    
    # Comando de ffmpeg optimizado para segmentación precisa
    cmd = [
        "ffmpeg",
        "-i", ruta_video_local,
        "-c:v", "libx264",  # Recodificar video para asegurar keyframes exactos
        "-x264-params", "keyint={0}:min-keyint={0}:force-cfr=1:scenecut=0".format(int(duracion_segmento*30)),
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
        
        # Verificar los fragmentos generados
        fragmentos = sorted([
            f for f in os.listdir(carpeta_salida)
            if f.startswith(f"{nombre_base}_segment_") and f.endswith(f".{formato_salida}")
        ])
        
        print(f"¡Fragmentación completada! {len(fragmentos)} segmentos generados en: {carpeta_salida}")
        
        # Verificar duración de cada fragmento
        if fragmentos:
            print("\nVerificando duración de los segmentos...")
            for i, fragmento in enumerate(fragmentos[:-1]):  # El último puede ser más corto
                ruta_fragmento = os.path.join(carpeta_salida, fragmento)
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
        
    except subprocess.CalledProcessError as e:
        print(f"Error al fragmentar el video: {e}")
        print("Asegúrate de que FFmpeg está instalado y accesible en tu PATH.")
    except Exception as e:
        print(f"Error inesperado: {e}")

# Ejemplo de uso:
fragmentacion_local(
    ruta_video_local="/Users/wivboost/Downloads/fran.mkv",  # O .mkv
    carpeta_salida="/Users/wivboost/Downloads/mejorado2",
    duracion_segmento=16
)