FROM ubuntu:22.04

# Evitar preguntas interactivas
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    # Herramientas de red
    aircrack-ng \
    aircrack-ng \
    airodump-ng \
    aireplay-ng \
    airmon-ng \
    # Herramientas adicionales
    hashcat \
    hcxdumptool \
    hcxpcapngtool \
    bully \
    pixiewps \
    # Python y utilidades
    python3 \
    python3-pip \
    python3-venv \
    git \
    wget \
    curl \
    vim \
    net-tools \
    wireless-tools \
    iw \
    # Para interfaz web
    nginx \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar requirements primero (para cachear)
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copiar todo el código
COPY . .

# Descargar wordlists comunes
RUN mkdir -p /usr/share/wordlists/ && \
    wget -O /usr/share/wordlists/rockyou.txt.gz \
    https://github.com/brannondorsey/naive-hashcat/releases/download/data/rockyou.txt.gz && \
    gunzip /usr/share/wordlists/rockyou.txt.gz || true

# Crear directorios necesarios
RUN mkdir -p /tmp/wordlists /app/logs /app/data

# Configurar permisos
RUN chmod +x forcewpa2.py web_interface.py distributed_controller.py distributed_worker.py

# Exponer puertos
EXPOSE 5000  # Web interface
EXPOSE 5555  # Distributed mode

# Healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Comando por defecto (web interface)
CMD ["python3", "web_interface.py"]
