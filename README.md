# **Embeddings Wivboost**

Este repositorio es para explorar la alternativa de los embeddings para remplazar a Video Intelligence.

---

## **Descripción General**

El proyecto usa el modelo `multimodalembedding@001` para generar embeddings de 1408 dimensiones para segmentos de video, imágenes y texto. Estos embeddings se indexan en Vertex AI Vector Search para permitir búsquedas de similitud.

---

## **Objetivo**

Aún está pendiente la aprobación, así que el flujo de trabajo es temporal, y queda en espera de una actualización futura.

---

### **Flujo de trabajo:**

1. **Procesar video:** Se carga un video y se divide en segmentos de 4 segundos (para máximar la calidad de los embeddings).
2. **Generar Embeddings:** Se crea un embedding vectorial para cada segmento.
3. **Indexar en Vector Search:** Los embeddings se guardan como un archivo JSON en un bucket de GCS y se utilizan para poblar un índice de Vector Search.
4. **Búsqueda:** Una consulta de texto (o imagen) se convierte en un embedding para buscar los segmentos de video más relevantes en el índice.
5. **Visualizar Resultados:** Los segmentos de video encontrados se muestran en el notebook.

---

## **Tecnologías Utilizadas**

- **Google Cloud Platform (GCP)**
- **Vertex AI** (Modelo `multimodalembedding@001` y Vector Search)
- **Google Cloud Storage (GCS)**
- **Python 3** y **Jupyter Notebooks**
- **Bibliotecas:** `google-cloud-aiplatform`, `google-cloud-storage`, `pandas`, `numpy`

---

## **Estructura del Repositorio**

- **HelloEmbeddings.ipynb:** Notebook introductorio que muestra el proceso básico de generación de embeddings a partir de un video.
- **CargaEmbeddings.ipynb:** Notebook principal que implementa el flujo completo: generación de embeddings, indexación en Vector Search y búsqueda semántica.

---

## **Flujo de Trabajo y Uso**

### 1. Prerrequisitos y Configuración

- Tener un proyecto de Google Cloud con facturación y las APIs de Vertex AI y Cloud Storage activadas.
- Configurar el SDK de `gcloud`.
- Subir el video a analizar a un bucket de GCS.
- En `CargaEmbeddings.ipynb`, actualizar las variables de configuración: `PROJECT_ID`, `LOCATION`, `BUCKET_NAME` y `ruta_video`.

### 2. Generación y Carga de Embeddings

- En `CargaEmbeddings.ipynb`, ejecuta la sección **"Generamos los embeddings"** para procesar el video.
- Luego, ejecuta la sección **"Carga a Vector Search"** para guardar los embeddings como un archivo `.json` en tu bucket de GCS.

### 3. Creación del Índice en Vector Search

- En la consola de GCP, ve a **Vertex AI > Vector Search** y crea un Índice.
- Puebla el índice usando el archivo `.json` de GCS generado previamente.
- Crea un Endpoint de Índice y despliega tu índice en él.
- Copia el ID del endpoint y el ID del índice desplegado.

### 4. Búsqueda de Video

- Regresa a `CargaEmbeddings.ipynb` y actualiza las variables `INDEX_ENDPOINT_NAME` y `DEPLOYED_INDEX_ID` con los valores del paso anterior.
- En la sección **"Query a los embeddings"**, define tu consulta en la variable `texto_de_busqueda`.
- Ejecuta las celdas restantes para visualizar los segmentos de video que el modelo encontró como relevantes.

---


