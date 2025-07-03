import os
import json
import vertexai
from vertexai.generative_models import Part, GenerativeModel



# --- Variables de Entorno (se configuran en la Cloud Function) ---
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")
BIGQUERY_TABLE_ID = os.getenv("BIGQUERY_TABLE_ID")



# Inicializa Vertex AI una sola vez cuando la función se despliega
vertexai.init(project=PROJECT_ID, location=LOCATION)



def guardar_en_bigquery(datos_json: dict, uri: str):
    """Guarda los datos procesados en una tabla de BigQuery."""
    from google.cloud import bigquery
    
    cliente_bq = bigquery.Client()
    
    fila_a_insertar = [{
        "uri_video": uri,
        "resultado_gemini": json.dumps(datos_json), # Convierte el dict a string JSON
        "fecha_procesamiento": "AUTO" # BigQuery asignará la fecha actual
    }]
    
    errores = cliente_bq.insert_rows_json(BIGQUERY_TABLE_ID, fila_a_insertar)
    if not errores:
        print(f"Resultados de {uri} guardados en BigQuery exitosamente.")
    else:
        print(f"Errores al guardar en BigQuery para {uri}: {errores}")



def reporteGemini(uri_completa: str, marca_a_buscar: str):
    """Llama a la API de Gemini para analizar un video desde su URI completa."""
    video = Part.from_uri(uri=uri_completa, mime_type='video/mkv')
    
    generation_config = {
        'temperature': 0.0,
        'max_output_tokens': 8192
    }
    
    system_instruction = """
Eres un analista de medios y publicidad de élite. Tu análisis debe ser contextual y preciso, siguiendo un proceso de decisión en dos etapas.

---
**ETAPA 1: ANÁLISIS DEL CONTEXTO GENERAL DEL CLIP**
---
Primero, evalúa la naturaleza general del video completo.
- ¿Es una **Transmisión en Vivo** del partido, mostrando el juego, a los jugadores en la cancha o a los fans en las gradas, sobre la cual se superponen gráficos?
- ¿O es un **Anuncio Producido**, que interrumpe el juego para contar una historia o mensaje publicitario con edición cinematográfica, música y actores, aunque muestre escenas de fútbol?

**Esta primera evaluación es la más importante.**

---
**ETAPA 2: CLASIFICACIÓN BASADA EN EL CONTEXTO**
---
Una vez determinado el contexto, aplica la siguiente regla:

1.  **Si el contexto es un 'Anuncio Producido':**
    La respuesta DEBE contener una única entrada para la marca. Usa la categoría **'Anuncio'** para la duración completa del clip. **NO reportes las apariciones individuales** de la marca dentro del propio comercial (en vallas, playeras, etc.).

2.  **Si el contexto es una 'Transmisión en Vivo':**
    Entonces, y solo entonces, procede a identificar y reportar cada aparición individual de la marca, eligiendo la categoría más apropiada de la siguiente lista:
    - **'Virtual'**: Gráfico generado por computadora superpuesto al campo mientras el juego continúa viéndose de fondo (ej. la botella de Yakult flotando).
    - **'Valla'**: La marca en las vallas LED físicas que rodean el campo.
    - **'Spot'**: Un gráfico que se sobrepone a la imagen sin estar integrado en el campo.
    - **'Banner'**: Un gráfico en los bordes de la pantalla.
    - **'Marcador'**: La marca junto al marcador de resultado.
    - **'Playera'**: El logo en la camiseta.
    - **'Menciones verbales'**: En comentarios o anuncios

### Formato de Salida Obligatorio
- Tu respuesta debe ser únicamente un objeto JSON con la clave "apariciones".
- Si no hay apariciones, devuelve: `{"apariciones": []}`.
- No incluyas explicaciones. Solo el JSON.

**Ejemplo de la estructura exacta que debes seguir:**
```json
{
  "apariciones": [
    {
      "marca": "Coca",
      "categoria": "Valla",
      "inicio": "00:11",
      "fin": "00:15"
    }
  ]
}

"""
    
    prompt_instruccion = "Busca en el video adjunto todas las apariciones (si es que existen) de la siguiente marca: "
    model = GenerativeModel('gemini-2.5-pro', system_instruction=system_instruction)
    
    contenido = [video, prompt_instruccion, marca_a_buscar]
    
    respuesta = model.generate_content(
        contents=contenido,
        generation_config=generation_config
    )
    
    return respuesta.text

def pasar_json(respuesta_gemini: str):
    """Limpia la respuesta de texto y la convierte en un objeto JSON."""
    try:
        json_limpio_str = respuesta_gemini.strip().removeprefix('```json').removesuffix('```').strip()
        return json.loads(json_limpio_str)
    except Exception as e:
        print(f"Error al parsear JSON: {e}")
        return None

def procesar_video(event, context):
    """
    Función principal que se activa cuando se sube un archivo a GCS.
    """
    bucket = event['bucket']
    nombre_archivo = event['name']
    
    # Ignora archivos que no estén en la carpeta deseada
    if not nombre_archivo.startswith('Videos/Prueba/'):
        print(f"Archivo {nombre_archivo} ignorado por no estar en la carpeta de entrada.")
        return

    uri_completa = f"gs://{bucket}/{nombre_archivo}"
    print(f"Procesando video: {uri_completa}")
    
    try:
        # Llama a la lógica de análisis
        respuesta_texto = reporteGemini(uri_completa, 'Caliente')
        resultado_json = pasar_json(respuesta_texto)
        
        if resultado_json:
            # Guarda el resultado en BigQuery
            guardar_en_bigquery(resultado_json, uri_completa)
            
    except Exception as e:
        print(f"Error fatal al procesar {uri_completa}: {e}")