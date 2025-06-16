FROM python:3.13.3

# Establecemos un directorio de trabajo.
WORKDIR /workspace

# Actualizamos los paquetes del sistema e instalamos ffmpeg.
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg

# Copiamos el código de nuestra función (main.py y requirements.txt) al contenedor.
COPY . .

# Instalamos las dependencias de Python.
RUN pip install --no-cache-dir -r requirements.txt

# Le decimos a Google cómo ejecutar la función.
ENV FUNCTION_TARGET=split_video_pipeline
CMD ["functions-framework", "--target", "split_video_pipeline", "--port", "8080"]