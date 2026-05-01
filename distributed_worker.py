#!/usr/bin/env python3
"""
Worker para modo distribuido
"""

import socket
import json
import threading
import time
import os
import subprocess
import multiprocessing

class DistributedWorker:
    def __init__(self, master_host, master_port=5555):
        self.master_host = master_host
        self.master_port = master_port
        self.worker_id = f"{socket.gethostname()}_{os.getpid()}"
        self.running = True
        self.current_task = None
    
    def get_capabilities(self):
        """Obtiene capacidades del worker"""
        # Detectar GPU
        has_gpu = False
        try:
            result = subprocess.run("nvidia-smi", shell=True, capture_output=True)
            has_gpu = result.returncode == 0
        except:
            pass
        
        # Detectar CPU cores
        cpu_cores = multiprocessing.cpu_count()
        
        return {
            'worker_id': self.worker_id,
            'has_gpu': has_gpu,
            'cpu_cores': cpu_cores,
            'hostname': socket.gethostname(),
            'os': os.name
        }
    
    def start(self):
        """Conecta al maestro y espera tareas"""
        while self.running:
            try:
                # Conectar al maestro
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((self.master_host, self.master_port))
                
                # Enviar capabilities
                capabilities = self.get_capabilities()
                sock.send(json.dumps(capabilities).encode())
                
                print(f"[Worker {self.worker_id}] Conectado al maestro")
                
                # Hilo para enviar heartbeats
                def send_heartbeat():
                    while self.running:
                        time.sleep(15)
                        try:
                            heartbeat = json.dumps({'type': 'heartbeat'})
                            sock.send(heartbeat.encode())
                        except:
                            break
                
                heartbeat_thread = threading.Thread(target=send_heartbeat)
                heartbeat_thread.daemon = True
                heartbeat_thread.start()
                
                # Escuchar tareas
                while self.running:
                    data = sock.recv(4096).decode()
                    if not data:
                        break
                    
                    task = json.loads(data)
                    if task['type'] == 'task':
                        self.execute_task(sock, task)
                
            except Exception as e:
                print(f"[Worker] Error: {e}, reconectando en 5s...")
                time.sleep(5)
    
    def execute_task(self, sock, task):
        """Ejecuta tarea recibida"""
        task_id = task['task_id']
        bssid = task['bssid']
        essid = task['essid']
        handshake_file = task['handshake_file']
        
        print(f"[Worker] Ejecutando tarea {task_id}: {essid}")
        
        # Enviar progreso
        def send_progress(progress):
            msg = json.dumps({
                'type': 'progress',
                'task_id': task_id,
                'progress': progress
            })
            sock.send(msg.encode())
        
        send_progress(0)
        
        # Ejecutar crackeo (ejemplo con aircrack)
        wordlist = "/usr/share/wordlists/rockyou.txt"
        cmd = f"aircrack-ng -w {wordlist} {handshake_file}"
        
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Monitorear progreso
        for line in process.stdout:
            if "KEY FOUND" in line:
                # Extraer contraseña
                import re
                match = re.search(r'KEY FOUND! \[ (.*) \]', line)
                if match:
                    password = match.group(1)
                    
                    # Enviar resultado
                    result = json.dumps({
                        'type': 'result',
                        'task_id': task_id,
                        'password': password,
                        'success': True
                    })
                    sock.send(result.encode())
                    print(f"[Worker] ✅ Contraseña encontrada: {password}")
                    return
        
        # Si llega aquí, no encontró
        result = json.dumps({
            'type': 'result',
            'task_id': task_id,
            'success': False,
            'message': 'Password not found in wordlist'
        })
        sock.send(result.encode())
        
        send_progress(100)

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Uso: distributed_worker.py <MASTER_IP>")
        sys.exit(1)
    
    worker = DistributedWorker(sys.argv[1])
    worker.start()
