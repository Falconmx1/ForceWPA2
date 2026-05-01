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
