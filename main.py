import requests
from ultralytics import YOLO
import os

TOKEN = "8786181093:AAG-pTaQrxOrFTn1n9j147gIrSVKm9mKHKo"
CHAT_ID = "6321825586"

def send_telegram_alert(message, image_path=None):
    msg_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(msg_url, json={"chat_id": CHAT_ID, "text": message})
    
    if image_path and os.path.exists(image_path):
        img_url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
        with open(image_path, 'rb') as photo:
            requests.post(img_url, data={'chat_id': CHAT_ID}, files={'photo': photo})

model = YOLO('best.pt') 
source_image = 'test.jpg'

results = model.predict(source=source_image, save=True, conf=0.25)

for result in results:
    num_objects = len(result.boxes)
    print(f"Détection: {num_objects} corps")
    
    if num_objects > 0:
        print("Envoi de l'alerte Telegram...")
        saved_image_path = os.path.join(result.save_dir, source_image)
        alert_text = f"🚨 risque : {num_objects} foyer(s) d'incendie détecté(s) !"
        send_telegram_alert(alert_text, saved_image_path)
    else:
        print("Statut: Aucun danger détecté.")