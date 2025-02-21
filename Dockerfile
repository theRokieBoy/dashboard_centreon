# Usa Python 3.10 como base
FROM python:3.10-slim

# Instala dependencias del sistema necesarias para mysqlclient
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Establece el directorio de trabajo
WORKDIR /app

# Copia los archivos de la aplicación al contenedor
COPY . .

# Instala las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Expone el puerto de Flask
EXPOSE 5000

# Comando para ejecutar la aplicación
CMD ["python", "app.py"]

