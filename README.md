# ForceWPA2 ⚡

Herramienta automatizada para auditoría WPA2: captura de handshake + fuerza bruta con GPU.

## ⚠️ LEGAL DISCLAIMER
**Solo para uso educativo y auditorías con autorización expresa.**  
Usar contra redes sin permiso es **ilegal**. El autor no se hace responsable.

## 🚀 Funcionalidades
- Captura de handshake (aireplay-ng / scapy)
- Deauth attack para forzar reconexión
- Fuerza bruta con wordlist (rockyou.txt o custom)
- **Soporte GPU** via hashcat
- Diccionarios integrados + descarga automática de rockyou.txt

## 📦 Requisitos
```bash
sudo apt install aircrack-ng hashcat
pip install scapy

🚀 Cómo ejecutar TODO

# Instalar dependencias
pip install -r requirements.txt

# Modo normal con todas las funciones
sudo python3 forcewpa2.py -i wlan0 -b AA:BB:CC:DD:EE:FF --persistent --gpu --notify

# Modo persistente (reintenta automáticamente)
sudo python3 forcewpa2.py -i wlan0 --persistent --max-attempts 20

# Generar wordlist personalizada desde ESSID
python3 -c "from modules.wordlist_generator import WordlistGenerator; g=WordlistGenerator(); g.generate_comprehensive('MiWifi123', 'AA:BB:CC:DD:EE:FF')"

# Interfaz web
sudo python3 web_interface.py

# Modo distribuido (maestro)
sudo python3 distributed_controller.py

# Modo distribuido (worker en otra máquina)
python3 distributed_worker.py 192.168.1.100

# Con integración de APIs
export DISCORD_WEBHOOK="https://discord.com/api/webhooks/..."
sudo python3 forcewpa2.py -i wlan0 --use-api --api-key YOUR_KEY
