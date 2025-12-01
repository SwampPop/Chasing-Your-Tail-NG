import requests
import logging
import os
import platform
import threading

# Load secure config to get credentials
from secure_credentials import secure_config_loader

logger = logging.getLogger(__name__)

class AlertManager:
    def __init__(self):
        self.config, self.creds = secure_config_loader('config.json')
        
        # You will need to add these to your vault later!
        self.bot_token = self.creds.get_credential("telegram", "token")
        self.chat_id = self.creds.get_credential("telegram", "chat_id")

    def send_alert(self, message, priority="low"):
        """
        Sends an alert via multiple channels (Audio, Telegram)
        """
        # 1. Audio Alert (Immediate/Offline)
        self._speak_alert(message)
        
        # 2. Telegram Alert (Rich Data/Online)
        if self.bot_token and self.chat_id:
            # Run in a separate thread so it doesn't slow down the scanner
            threading.Thread(target=self._send_telegram, args=(message,)).start()
        else:
            logger.warning("Telegram credentials not found. Skipping remote alert.")

    def _speak_alert(self, text):
        """Uses system Text-to-Speech"""
        system = platform.system()
        
        # Clean text for speech (remove special chars)
        clean_text = text.replace("[!!!]", "Alert").replace("\n", ". ")
        
        if system == "Darwin": # macOS
            os.system(f'say "{clean_text}" &')
        elif system == "Linux": # Raspberry Pi
            # On Pi, we usually use 'espeak' or just a buzzer
            # os.system(f'espeak "{clean_text}" &')
            pass

    def _send_telegram(self, text):
        """Push notification to phone"""
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        data = {"chat_id": self.chat_id, "text": text}
        try:
            requests.post(url, data=data, timeout=5)
        except Exception as e:
            logger.error(f"Failed to send Telegram: {e}")

# Helper for simple usage
def send_drone_alert(manuf, mac):
    alerter = AlertManager()
    msg = f"⚠️ DRONE DETECTED ⚠️\nType: {manuf}\nID: {mac}"
    alerter.send_alert(msg)

def send_stalker_alert(mac, count):
    alerter = AlertManager()
    msg = f"👁️ PERSISTENCE ALERT 👁️\nTarget: {mac}\nSeen count: {count}"
    alerter.send_alert(msg)
