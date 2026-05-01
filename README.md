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

🚀 Comandos de uso rápido
# Dar permisos de ejecución
chmod +x forcewpa2.py

# Modo escaneo (solo ver redes)
sudo python3 forcewpa2.py -i wlan0 --scan-only

# Ataque completo (captura + brute force con CPU)
sudo python3 forcewpa2.py -i wlan0 -b AA:BB:CC:DD:EE:FF -c 6 -w rockyou.txt

# Con GPU (hashcat)
sudo python3 forcewpa2.py -i wlan0 -b AA:BB:CC:DD:EE:FF -c 6 -w rockyou.txt --gpu

# Modo interactivo (escanea y te deja elegir objetivo)
sudo python3 forcewpa2.py -i wlan0
