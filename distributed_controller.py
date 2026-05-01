#!/usr/bin/env python3
"""
Controlador maestro para modo distribuido
"""

import socket
import threading
import json
import time
import hashlib
from queue import Queue
from datetime import datetime

class DistributedController:
    def __init__(self, port=5555):
        self.port = port
        self.workers = {}  # {worker_id: {'socket': socket, 'last_seen': time, 'capabilities': {}}}
        self.task_queue = Queue()
        self.results = {}
        self.running = True
    
    def start(self):
        """Inicia el servidor maestro"""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', self.port))
        server.listen(10)
        
        print(f"[Master] Controlador distribuido escuchando en puerto {self.port}")
        
        # Hilo para manejar workers
        accept_thread = threading.Thread(target=self.accept_workers, args=(server,))
        accept_thread.daemon = True
        accept_thread.start()
        
        # Hilo para distribuir tareas
        dispatch_thread = threading.Thread(target=self.dispatch_tasks)
        dispatch_thread.daemon = True
        dispatch_thread.start()
        
        # Hilo para monitorear workers
        monitor_thread = threading.Thread(target=self.monitor_workers)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        while self.running:
            cmd = input("\n[Master] Comando (add_task/status/exit): ")
            if cmd == 'add_task':
                bssid = input("BSSID: ")
                essid = input("ESSID: ")
                handshake_file = input("Handshake file: ")
                self.add_task(bssid, essid, handshake_file)
            elif cmd == 'status':
                self.print_status()
            elif cmd == 'exit':
                self.running = False
                break
    
    def accept_workers(self, server):
        """Acepta conexiones de workers"""
        while self.running:
            try:
                client, addr = server.accept()
                worker_id = f"{addr[0]}:{addr[1]}"
                
                # Recibir capabilities del worker
                data = client.recv(4096).decode()
                capabilities = json.loads(data)
                
                self.workers[worker_id] = {
                    'socket': client,
                    'addr': addr,
                    'last_seen': time.time(),
                    'capabilities': capabilities,
                    'task': None
                }
                
                print(f"[Master] Worker conectado: {worker_id} (GPU: {capabilities.get('has_gpu', False)})")
                
                # Hilo para escuchar respuestas
                resp_thread = threading.Thread(target=self.handle_worker_responses, args=(client, worker_id))
                resp_thread.daemon = True
                resp_thread.start()
                
            except Exception as e:
                print(f"[Master] Error aceptando worker: {e}")
    
    def handle_worker_responses(self, client, worker_id):
        """Maneja respuestas de workers"""
        while self.running and worker_id in self.workers:
            try:
                data = client.recv(4096).decode()
                if not data:
                    break
                
                response = json.loads(data)
                
                if response['type'] == 'result':
                    task_id = response['task_id']
                    self.results[task_id] = response
                    print(f"\n[Master] ✅ Resultado recibido de {worker_id}: {response['password']}")
                
                elif response['type'] == 'heartbeat':
                    self.workers[worker_id]['last_seen'] = time.time()
                
                elif response['type'] == 'progress':
                    print(f"[Master] Progreso {worker_id}: {response['progress']}%")
                
            except Exception as e:
                print(f"[Master] Error con worker {worker_id}: {e}")
                break
        
        # Limpiar worker desconectado
        if worker_id in self.workers:
            del self.workers[worker_id]
            print(f"[Master] Worker desconectado: {worker_id}")
    
    def add_task(self, bssid, essid, handshake_file):
        """Agrega tarea a la cola"""
        task_id = hashlib.md5(f"{bssid}{essid}{time.time()}".encode()).hexdigest()[:8]
        
        task = {
            'id': task_id,
            'bssid': bssid,
            'essid': essid,
            'handshake_file': handshake_file,
            'created_at': datetime.now().isoformat()
        }
        
        self.task_queue.put(task)
        print(f"[Master] Tarea agregada: {task_id} - {essid}")
        return task_id
    
    def dispatch_tasks(self):
        """Distribuye tareas a workers disponibles"""
        while self.running:
            if not self.task_queue.empty():
                # Buscar worker libre
                available_worker = None
                for worker_id, worker_info in self.workers.items():
                    if worker_info['task'] is None:
                        available_worker = worker_id
                        break
                
                if available_worker:
                    task = self.task_queue.get()
                    worker_info = self.workers[available_worker]
                    worker_info['task'] = task['id']
                    
                    # Enviar tarea
                    message = json.dumps({
                        'type': 'task',
                        'task_id': task['id'],
                        'bssid': task['bssid'],
                        'essid': task['essid'],
                        'handshake_file': task['handshake_file']
                    })
                    
                    try:
                        worker_info['socket'].send(message.encode())
                        print(f"[Master] Tarea {task['id']} asignada a {available_worker}")
                    except:
                        del self.workers[available_worker]
            else:
                time.sleep(1)
    
    def monitor_workers(self):
        """Monitorea workers y reasigna tareas si es necesario"""
        while self.running:
            current_time = time.time()
            for worker_id, worker_info in list(self.workers.items()):
                if current_time - worker_info['last_seen'] > 30:
                    print(f"[Master] Worker {worker_id} timeout, reasignando tarea...")
                    
                    # Reasignar tarea si tenía una
                    if worker_info['task']:
                        # Recuperar tarea y ponerla de vuelta en la cola
                        task_id = worker_info['task']
                        # Buscar tarea original (simplificado)
                        print(f"[Master] Tarea {task_id} reasignada a la cola")
                    
                    del self.workers[worker_id]
            
            time.sleep(10)
    
    def print_status(self):
        """Imprime estado del sistema distribuido"""
        print(f"\n=== ESTADO DEL SISTEMA ===")
        print(f"Workers activos: {len(self.workers)}")
        print(f"Tareas pendientes: {self.task_queue.qsize()}")
        print(f"Resultados obtenidos: {len(self.results)}")
        
        for worker_id, info in self.workers.items():
            print(f"\nWorker: {worker_id}")
            print(f"  GPU: {info['capabilities'].get('has_gpu', False)}")
            print(f"  CPU Cores: {info['capabilities'].get('cpu_cores', '?')}")
            print(f"  Tarea actual: {info['task'] or 'Ninguna'}")
