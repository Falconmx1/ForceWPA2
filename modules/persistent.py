#!/usr/bin/env python3
"""
Modo persistente - Reintentos automáticos con backoff exponencial
"""

import time
import json
import sqlite3
from datetime import datetime, timedelta
from threading import Thread, Event

class PersistentMode:
    def __init__(self, db_path="persistent_results.db"):
        self.db_path = db_path
        self.running = False
        self.thread = None
        self.stop_event = Event()
        self.init_database()
    
    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bssid TEXT,
                essid TEXT,
                channel TEXT,
                status TEXT,
                attempts INTEGER DEFAULT 0,
                max_attempts INTEGER DEFAULT 10,
                last_attempt TIMESTAMP,
                next_attempt TIMESTAMP,
                password TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bssid TEXT,
                essid TEXT,
                password TEXT,
                attempts INTEGER,
                time_found TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    
    def add_job(self, bssid, essid, channel, max_attempts=10):
        """Agrega un trabajo persistente"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO jobs (bssid, essid, channel, status, attempts, max_attempts, next_attempt)
            VALUES (?, ?, ?, 'pending', 0, ?, ?)
        ''', (bssid, essid, channel, max_attempts, datetime.now()))
        conn.commit()
        job_id = cursor.lastrowid
        conn.close()
        return job_id
    
    def get_pending_jobs(self):
        """Obtiene trabajos pendientes"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, bssid, essid, channel, attempts, max_attempts
            FROM jobs 
            WHERE status IN ('pending', 'retry') 
            AND next_attempt <= ?
            ORDER BY attempts ASC
        ''', (datetime.now(),))
        jobs = cursor.fetchall()
        conn.close()
        return jobs
    
    def update_job_status(self, job_id, status, password=None):
        """Actualiza estado del trabajo"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if status == 'success' and password:
            cursor.execute('''
                UPDATE jobs SET status=?, password=?, last_attempt=?
                WHERE id=?
            ''', (status, password, datetime.now(), job_id))
            
            # Guardar en resultados
            cursor.execute('''
                INSERT INTO results (bssid, essid, password, attempts, time_found)
                SELECT bssid, essid, ?, attempts, ?
                FROM jobs WHERE id=?
            ''', (password, datetime.now(), job_id))
        else:
            cursor.execute('''
                UPDATE jobs 
                SET status=?, attempts=attempts+1, last_attempt=?
                WHERE id=?
            ''', (status, datetime.now(), job_id))
            
            # Calcular próximo intento (backoff exponencial)
            cursor.execute('SELECT attempts FROM jobs WHERE id=?', (job_id,))
            attempts = cursor.fetchone()[0]
            
            # Espera exponencial: 1min, 2min, 4min, 8min, hasta 1 hora
            wait_minutes = min(2 ** (attempts - 1), 60)
            next_time = datetime.now() + timedelta(minutes=wait_minutes)
            
            if attempts < 10:  # Si no superó máximo
                cursor.execute('''
                    UPDATE jobs SET next_attempt=?, status='retry'
                    WHERE id=?
                ''', (next_time, job_id))
        
        conn.commit()
        conn.close()
    
    def run_persistent_loop(self, attack_function):
        """Loop principal persistente"""
        print("[Persistent] Modo persistente activado - Reintentando automáticamente")
        
        while not self.stop_event.is_set():
            jobs = self.get_pending_jobs()
            
            for job in jobs:
                job_id, bssid, essid, channel, attempts, max_attempts = job
                
                print(f"[Persistent] Intentando {bssid} ({essid}) - Intento {attempts+1}/{max_attempts}")
                
                try:
                    # Ejecutar la función de ataque
                    success, password = attack_function(bssid, essid, channel)
                    
                    if success:
                        self.update_job_status(job_id, 'success', password)
                        print(f"[Persistent] ✅ ÉXITO! Contraseña: {password}")
                    else:
                        if attempts + 1 >= max_attempts:
                            self.update_job_status(job_id, 'failed')
                            print(f"[Persistent] ❌ Falló después de {max_attempts} intentos")
                        else:
                            self.update_job_status(job_id, 'retry')
                            print(f"[Persistent] ⏳ Reintentando más tarde...")
                except Exception as e:
                    print(f"[Persistent] Error: {e}")
                    self.update_job_status(job_id, 'error')
            
            time.sleep(30)  # Revisar cada 30 segundos
    
    def start(self, attack_function):
        """Inicia modo persistente en background"""
        if not self.running:
            self.running = True
            self.stop_event.clear()
            self.thread = Thread(target=self.run_persistent_loop, args=(attack_function,))
            self.thread.daemon = True
            self.thread.start()
            return True
        return False
    
    def stop(self):
        """Detiene modo persistente"""
        self.running = False
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=5)
        return True
    
    def get_stats(self):
        """Estadísticas de trabajos"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT status, COUNT(*) FROM jobs GROUP BY status
        ''')
        stats = dict(cursor.fetchall())
        conn.close()
        return stats
