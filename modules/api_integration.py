#!/usr/bin/env python3
"""
Integración con APIs externas para wordlists
"""

import requests
import json
import time
from concurrent.futures import ThreadPoolExecutor

class APIIntegration:
    def __init__(self):
        self.apis = {
            'hibp': {
                'url': 'https://api.pwnedpasswords.com/range/{}',
                'enabled': True
            },
            'weakpass': {
                'url': 'https://weakpass.com/api/v1/search/{}',
                'enabled': True
            },
            'haveibeenpwned_breaches': {
                'url': 'https://haveibeenpwned.com/api/v3/breachedaccount/{}',
                'enabled': True
            }
        }
        self.cache = {}
    
    def query_hibp(self, hash_prefix):
        """Consulta HaveIBeenPwned API para contraseñas filtradas"""
        try:
            url = self.apis['hibp']['url'].format(hash_prefix)
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return response.text
        except:
            pass
        return None
    
    def get_weakpass_list(self, keyword, limit=100):
        """Obtiene contraseñas relacionadas de Weakpass"""
        try:
            url = self.apis['weakpass']['url'].format(keyword)
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                passwords = data.get('passwords', [])[:limit]
                return passwords
        except:
            pass
        return []
    
    def generate_smart_wordlist(self, essid, bssid, context_words=None):
        """
        Genera wordlist inteligente basada en contexto
        """
        wordlist = set()
        
        # Basado en ESSID
        essid_clean = re.sub(r'[^a-zA-Z0-9]', '', essid)
        wordlist.add(essid_clean)
        wordlist.add(essid_clean.lower())
        wordlist.add(essid_clean.upper())
        
        # Basado en BSSID (últimos bytes)
        bssid_parts = bssid.split(':')
        if len(bssid_parts) >= 3:
            last_bytes = ''.join(bssid_parts[-3:])
            wordlist.add(last_bytes)
        
        # Años comunes
        current_year = time.localtime().tm_year
        for year in range(current_year - 10, current_year + 1):
            wordlist.add(str(year))
            wordlist.add(str(year)[-2:])
        
        # Números comunes
        for num in ['123', '1234', '12345', '123456', '12345678', '0000', '1111', 'password']:
            wordlist.add(num)
        
        # Palabras contextuales
        if context_words:
            for word in context_words:
                wordlist.add(word)
        
        # Variaciones comunes
        suffixes = ['', '1', '12', '123', '!', '?', '@', '#', '2023', '2024']
        new_words = set()
        for word in wordlist:
            for suffix in suffixes:
                new_words.add(f"{word}{suffix}")
                new_words.add(f"{word}{suffix.upper()}")
        
        wordlist.update(new_words)
        
        return list(wordlist)[:5000]  # Limitar a 5000
    
    def get_breached_passwords_for_email(self, email):
        """Obtiene contraseñas filtradas asociadas a un email"""
        try:
            url = self.apis['haveibeenpwned_breaches']['url'].format(email)
            headers = {'hibp-api-key': 'your-key-here'}  # Requiere API key gratis
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                breaches = response.json()
                # Los breaches no dan las contraseñas directamente, pero podemos inferir patrones
                return [breach.get('Name', '') for breach in breaches]
        except:
            pass
        return []
    
    def download_weakpass_category(self, category, output_file):
        """Descarga wordlist completa de Weakpass"""
        categories = {
            'rockyou': 'https://weakpass.com/wordlists/rockyou.txt',
            'phpbb': 'https://weakpass.com/wordlists/phpbb.txt',
            'linkedin': 'https://weakpass.com/wordlists/linkedin.txt'
        }
        
        if category in categories:
            print(f"[API] Descargando wordlist de Weakpass: {category}")
            response = requests.get(categories[category], stream=True)
            
            with open(output_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return output_file
        return None
