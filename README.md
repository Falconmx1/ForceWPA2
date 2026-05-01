# 🔓 ForceWPA2 Pro

<div align="center">

![Version](https://img.shields.io/badge/version-3.0.0-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)
![License](https://img.shields.io/badge/license-GPLv3-red)
![Docker](https://img.shields.io/badge/docker-ready-blue)
![Tests](https://img.shields.io/badge/tests-95%25-brightgreen)

**Herramienta profesional de auditoría WPA2/WPA3 con soporte GPU, modo distribuido y múltiples integraciones**

[Características](#-características) • [Instalación](#-instalación) • [Docker](#-docker) • [Uso](#-uso) • [API](#-api) • [Tests](#-tests)

</div>

---

## ⚠️ **ADVERTENCIA LEGAL**

> **Esta herramienta es SOLO para fines educativos y auditorías autorizadas.**
> El uso contra redes sin permiso explícito es **ILEGAL** en la mayoría de países.
> El autor no se responsabiliza por mal uso.

---

## ✨ Características

### 🎯 Core
- ✅ Captura de handshake WPA2/WPA3
- ✅ Ataque de deauth personalizable
- ✅ Fuerza bruta con diccionario
- ✅ Soporte GPU (hashcat)
- ✅ Ataque PMKID (sin clients)
- ✅ Ataque WPS (bully/pixiewps)

### 🚀 Avanzado
- 🔄 **Modo persistente** - Reintentos automáticos con backoff exponencial
- 🌐 **Modo distribuido** - Múltiples workers en paralelo
- 📱 **Notificaciones** - Telegram, Discord, Slack, Email, Webhooks
- 🧠 **Wordlist inteligente** - Generación basada en contexto
- 🔌 **API externas** - HaveIBeenPwned, Weakpass
- 🎨 **Interfaz web** - Panel de control completo
- 🐳 **Docker ready** - Despliegue en un comando

### 📊 Modos de ataque
| Modo | Descripción | Velocidad |
|------|-------------|-----------|
| Diccionario | Wordlist tradicional | ⭐⭐ |
| GPU (hashcat) | Aceleración por GPU | ⭐⭐⭐⭐⭐ |
| Máscara | Ataque por patrón | ⭐⭐⭐⭐ |
| Reglas | Mutación de diccionario | ⭐⭐⭐ |
| WPS | Pin brute force | ⭐⭐ |
| PMKID | Sin clients necesarios | ⭐⭐⭐ |

---

## 📦 Instalación

### Opción 1: Instalación directa

```bash
# Clonar repositorio
git clone https://github.com/Falconmx1/ForceWPA2.git
cd ForceWPA2

# Instalar dependencias del sistema (Kali/Parrot/Ubuntu)
sudo apt update
sudo apt install -y aircrack-ng hashcat hcxdumptool bully pixiewps

# Instalar dependencias Python
pip3 install -r requirements.txt

# Descargar wordlist (opcional)
sudo wget -O /usr/share/wordlists/rockyou.txt.gz \
    https://github.com/brannondorsey/naive-hashcat/releases/download/data/rockyou.txt.gz
sudo gunzip /usr/share/wordlists/rockyou.txt.gz

# Ejecutar
sudo python3 forcewpa2.py -i wlan0 --scan-only

Opción 2: Docker (recomendado)
# Usar docker-compose (todo incluido)
docker-compose up -d

# O solo el contenedor principal
docker build -t forcewpa2 .
docker run --privileged --network host -it forcewpa2

# Con variables de entorno
docker run --privileged --network host \
    -e TELEGRAM_BOT_TOKEN="your_token" \
    -e NOTIFY_WEBHOOK="your_webhook" \
    forcewpa2

Opción 3: Desde Python (modo desarrollo)
# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar en modo desarrollo
pip install -e .

# Ejecutar
forcewpa2 -i wlan0

🚀 Uso Rápido
CLI Básico
# Escanear redes disponibles
sudo python3 forcewpa2.py -i wlan0 --scan-only

# Ataque completo (automático)
sudo python3 forcewpa2.py -i wlan0

# Ataque específico
sudo python3 forcewpa2.py -i wlan0 -b AA:BB:CC:DD:EE:FF -c 6 -w rockyou.txt

# Con GPU y notificaciones
sudo python3 forcewpa2.py -i wlan0 -b AA:BB:CC:DD:EE:FF --gpu --notify

# Modo persistente (reintenta hasta 20 veces)
sudo python3 forcewpa2.py -i wlan0 --persistent --max-attempts 20

# Ataque PMKID (más rápido)
sudo python3 forcewpa2.py -i wlan0 --pmkid

# Ataque WPS
sudo python3 forcewpa2.py -i wlan0 -b AA:BB:CC:DD:EE:FF --wps

Interfaz Web
# Iniciar servidor web
sudo python3 web_interface.py

# Acceder en navegador
http://localhost:5000

# Credenciales por defecto (si aplica)
admin / admin

Modo Distribuido
sudo python3 distributed_controller.py

# En máquinas WORKER (1..N)
python3 distributed_worker.py <MASTER_IP>

🔧 Configuración Avanzada
Notificaciones
# Configuración interactiva
python3 -c "from modules.notifications import setup_notifications_interactive; setup_notifications_interactive()"

# O manual: editar notifications_config.json
{
  "telegram": {
    "enabled": true,
    "bot_token": "123456:ABC-DEF",
    "chat_ids": ["123456789"]
  },
  "discord": {
    "enabled": true,
    "webhook_urls": ["https://discord.com/api/webhooks/..."]
  }
}

Wordlist Personalizada
from modules.wordlist_generator import WordlistGenerator

gen = WordlistGenerator()
file, count = gen.generate_comprehensive(
    essid="MiWifi",
    bssid="AA:BB:CC:DD:EE:FF",
    custom_seeds=["admin", "password"]
)
print(f"Generadas {count} contraseñas en {file}")

Variables de Entorno
# Crear archivo .env
cp .env.example .env
# Editar con tus credenciales

# Cargar variables
source .env

# Ejecutar con configuración
docker-compose --env-file .env up

📊 API Endpoints (Web Interface)
Endpoint	Método	Descripción
/api/scan	POST	Escanear redes WiFi
/api/attack/start	POST	Iniciar ataque
/api/attack/status/<id>	GET	Estado de ataque
/api/wordlist/generate	POST	Generar wordlist
/api/stats	GET	Estadísticas del sistema
/api/history	GET	Historial de ataques

🧪 Tests
# Ejecutar todos los tests
python3 -m pytest tests/

# Con coverage
pytest --cov=. --cov-report=html tests/

# Tests específicos
python3 tests/test_handshake.py
python3 tests/test_wordlist_generator.py

# Tests de rendimiento
python3 tests/test_handshake.py TestPerformance

🐳 Docker Commands
# Construir imagen
docker build -t forcewpa2:latest .

# Ejecutar con montaje de volúmenes
docker run --privileged --network host \
    -v $(pwd)/data:/app/data \
    -v $(pwd)/wordlists:/app/wordlists \
    -v $(pwd)/notifications_config.json:/app/notifications_config.json \
    -it forcewpa2

# Ver logs
docker logs -f forcewpa2-web

# Escalar workers en modo distribuido
docker-compose up --scale forcewpa2-worker=5 -d

# Limpiar todo
docker-compose down -v

📈 Rendimiento
Velocidades de crackeo (estimadas)
Hardware	Método	Velocidad (hashes/seg)
CPU Intel i5	Aircrack-ng	~2,000
CPU Intel i7	Aircrack-ng	~5,000
NVIDIA GTX 1060	Hashcat	~150,000
NVIDIA RTX 3080	Hashcat	~500,000
3x RTX 3090 (distribuido)	Hashcat	~2,000,000

Tiempos estimados (8 caracteres, alfanumérico)
Método	Tiempo estimado
CPU	~3 días
GPU (RTX 3080)	~2 horas
Distribuido (3 GPUs)	~40 minutos

🚀 Comandos rápidos para desplegar todo
# 1. Clonar
git clone https://github.com/Falconmx1/ForceWPA2.git
cd ForceWPA2

# 2. Configurar notificaciones
python3 -c "from modules.notifications import setup_notifications_interactive; setup_notifications_interactive()"

# 3. Levantar con Docker (recomendado)
docker-compose up -d

# 4. Abrir interfaz web
firefox http://localhost:5000

# 5. Ejecutar tests
python3 -m pytest tests/ -v

# 6. Modo producción (con workers)
docker-compose up --scale forcewpa2-worker=3 -d
