#!/usr/bin/env python3
"""
Generador avanzado de wordlists personalizadas
"""

import itertools
import re
from datetime import datetime

class WordlistGenerator:
    def __init__(self):
        self.common_words = [
            'admin', 'wifi', 'password', 'network', 'internet', 'router',
            'default', 'user', 'guest', 'home', 'family', 'house'
        ]
        
        self.common_numbers = [
            '123', '1234', '12345', '123456', '12345678', '0000', '1111',
            '111111', '888888', '123123', '112233', '121212', '131313'
        ]
        
        self.special_chars = ['!', '@', '#', '$', '%', '?', '*', '.', ',', '-', '_']
    
    def generate_from_essid(self, essid, max_length=12):
        """
        Genera wordlist basada en el nombre de la red
        """
        wordlist = set()
        
        # Limpiar ESSID
        essid_clean = re.sub(r'[^a-zA-Z0-9]', '', essid)
        
        # Variaciones de capitalización
        wordlist.add(essid_clean)
        wordlist.add(essid_clean.lower())
        wordlist.add(essid_clean.upper())
        wordlist.add(essid_clean.capitalize())
        
        # Añadir números comunes
        for num in self.common_numbers:
            wordlist.add(f"{essid_clean}{num}")
            wordlist.add(f"{num}{essid_clean}")
        
        # Variaciones leet
        leet_map = {
            'a': '4', 'e': '3', 'i': '1', 'o': '0', 's': '5', 't': '7', 'b': '8'
        }
        leet_word = ''.join([leet_map.get(c.lower(), c) for c in essid_clean])
        wordlist.add(leet_word)
        
        return list(wordlist)[:1000]
    
    def generate_from_location(self, location_info):
        """
        Genera wordlist basada en ubicación (ciudad, código postal, etc)
        """
        wordlist = set()
        
        # Ciudad, código postal, etc
        if 'city' in location_info:
            city = location_info['city']
            wordlist.add(city)
            wordlist.add(city.lower())
            wordlist.add(city.upper())
            
            for num in self.common_numbers[:5]:
                wordlist.add(f"{city}{num}")
        
        if 'postal_code' in location_info:
            wordlist.add(location_info['postal_code'])
        
        if 'street' in location_info:
            street_parts = location_info['street'].split()
            for part in street_parts:
                if len(part) > 3:
                    wordlist.add(part)
        
        return list(wordlist)[:500]
    
    def generate_date_patterns(self):
        """
        Genera patrones de fechas comunes
        """
        patterns = set()
        current = datetime.now()
        
        # Años
        for year in range(current.year - 20, current.year + 1):
            patterns.add(str(year))
            patterns.add(str(year)[-2:])
        
        # Meses
        for month in range(1, 13):
            patterns.add(f"{month:02d}")
            patterns.add(f"{month}")
        
        # Días
        for day in range(1, 32):
            patterns.add(f"{day:02d}")
            patterns.add(f"{day}")
        
        # Combinaciones comunes
        for year in range(current.year - 10, current.year + 1):
            for month in [1, 6, 12]:
                patterns.add(f"{year}{month:02d}")
                patterns.add(f"{month:02d}{year}")
                patterns.add(f"{day:02d}{month:02d}{year}")
        
        return list(patterns)
    
    def generate_masks_from_essid(self, essid):
        """
        Genera máscaras de ataque basadas en el ESSID
        """
        masks = set()
        
        # Tamaño de la contraseña objetivo
        for size in [8, 10, 12]:
            masks.add(f"?l?l?l?l?d?d?d?d")  # 4 letras + 4 números
            masks.add(f"?d?d?d?d?l?l?l?l")  # 4 números + 4 letras
            masks.add(f"?l?d?l?d?l?d?l?d")  # Alternado
        
        # Si ESSID tiene formato específico (ej: WiFi_XXXX)
        parts = re.split(r'[_-]', essid)
        if len(parts) > 1:
            word_part = parts[0]
            masks.add(f"{word_part}?d?d?d?d")
            masks.add(f"?d?d?d?d{word_part}")
        
        return list(masks)
    
    def generate_comprehensive(self, essid, bssid, custom_seeds=None):
        """
        Genera wordlist completa combinando todas las técnicas
        """
        full_list = set()
        
        # Desde ESSID
        full_list.update(self.generate_from_essid(essid))
        
        # Desde BSSID
        bssid_clean = bssid.replace(':', '')
        full_list.add(bssid_clean)
        full_list.add(bssid_clean[-6:])
        full_list.add(bssid_clean[-4:])
        
        # Fechas
        full_list.update(self.generate_date_patterns())
        
        # Palabras comunes
        full_list.update(self.common_words)
        full_list.update(self.common_numbers)
        
        # Semillas personalizadas
        if custom_seeds:
            full_list.update(custom_seeds)
        
        # Combinaciones
        combined = set()
        for word in list(full_list)[:100]:
            for num in self.common_numbers[:10]:
                combined.add(f"{word}{num}")
                combined.add(f"{num}{word}")
                for char in self.special_chars[:5]:
                    combined.add(f"{word}{char}")
                    combined.add(f"{char}{word}")
        
        full_list.update(combined)
        
        # Guardar a archivo
        output_file = f"wordlist_{essid}.txt"
        with open(output_file, 'w') as f:
            for password in sorted(full_list):
                if 8 <= len(password) <= 63:  # Longitud válida para WPA2
                    f.write(f"{password}\n")
        
        return output_file, len(full_list)
