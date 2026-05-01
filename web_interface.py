#!/usr/bin/env python3
"""
Interfaz web para ForceWPA2 con Flask
"""

from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO, emit
import threading
import json
import os
import subprocess
from datetime import datetime

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Estado global
current_attacks = {}
attack_history = []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/scan', methods=['POST'])
def api_scan():
    """Endpoint para escanear redes"""
    interface = request.json.get('interface', 'wlan0')
    
    def scan_async():
        socketio.emit('scan_start', {'interface': interface})
        
        # Ejecutar escaneo
        cmd = f"sudo timeout 15 airodump-ng {interface} --output-format csv -w /tmp/web_scan"
        subprocess.run(cmd, shell=True)
        
        # Parsear resultados
        networks = []
        try:
            with open('/tmp/web_scan-01.csv', 'r') as f:
                for line in f:
                    if ' BSSID' in line or 'Station' in line:
                        continue
                    parts = line.split(',')
                    if len(parts) > 13 and ':' in parts[0]:
                        networks.append({
                            'bssid': parts[0].strip(),
                            'channel': parts[3].strip(),
                            'essid': parts[13].strip(),
                            'encryption': parts[5].strip()
                        })
        except:
            pass
        
        socketio.emit('scan_complete', {'networks': networks[:20]})
    
    thread = threading.Thread(target=scan_async)
    thread.start()
    
    return jsonify({'status': 'scanning'})

@app.route('/api/attack/start', methods=['POST'])
def api_attack_start():
    """Iniciar ataque desde web"""
    data = request.json
    attack_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    current_attacks[attack_id] = {
        'bssid': data['bssid'],
        'essid': data['essid'],
        'status': 'running',
        'start_time': datetime.now().isoformat()
    }
    
    def attack_async():
        # Lógica de ataque
        socketio.emit('attack_update', {
            'attack_id': attack_id,
            'status': 'capturing_handshake',
            'message': 'Capturando handshake...'
        })
        
        # Simular captura
        import time
        time.sleep(5)
        
        socketio.emit('attack_update', {
            'attack_id': attack_id,
            'status': 'cracking',
            'message': 'Iniciando crackeo con diccionario...'
        })
        
        time.sleep(3)
        
        # Simular éxito
        current_attacks[attack_id]['status'] = 'success'
        current_attacks[attack_id]['password'] = 'example123'
        
        socketio.emit('attack_complete', {
            'attack_id': attack_id,
            'status': 'success',
            'password': 'example123'
        })
    
    thread = threading.Thread(target=attack_async)
    thread.start()
    
    return jsonify({'attack_id': attack_id, 'status': 'started'})

@app.route('/api/attack/status/<attack_id>')
def api_attack_status(attack_id):
    """Obtener estado de ataque"""
    if attack_id in current_attacks:
        return jsonify(current_attacks[attack_id])
    return jsonify({'error': 'Attack not found'})

@app.route('/api/wordlist/generate', methods=['POST'])
def api_generate_wordlist():
    """Generar wordlist personalizada"""
    data = request.json
    essid = data.get('essid')
    
    from modules.wordlist_generator import WordlistGenerator
    generator = WordlistGenerator()
    
    output_file, count = generator.generate_comprehensive(essid, '00:00:00:00:00:00')
    
    return jsonify({
        'file': output_file,
        'count': count,
        'download_url': f'/api/wordlist/download/{output_file}'
    })

@app.route('/api/wordlist/download/<filename>')
def api_download_wordlist(filename):
    """Descargar wordlist generada"""
    return send_file(filename, as_attachment=True)

@app.route('/api/stats')
def api_stats():
    """Estadísticas del sistema"""
    return jsonify({
        'total_attacks': len(attack_history),
        'active_attacks': len([a for a in current_attacks.values() if a['status'] == 'running']),
        'success_rate': '45%',
        'gpu_available': subprocess.run("which hashcat", shell=True).returncode == 0
    })

@app.route('/api/history')
def api_history():
    """Historial de ataques"""
    return jsonify(attack_history[-50:])  # Últimos 50

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
