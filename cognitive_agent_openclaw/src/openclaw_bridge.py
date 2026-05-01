#!/usr/bin/env python3
import os
import json
import time
import logging
import requests
import paho.mqtt.client as mqtt

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
FRIGATE_URL = os.getenv("FRIGATE_URL", "http://localhost:5000")
FRIGATE_USER = os.getenv("FRIGATE_USER", "admin")
FRIGATE_PASSWORD = os.getenv("FRIGATE_PASSWORD", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CAMERA_NAME = os.getenv("CAMERA_NAME", "front_door")
COOLDOWN_SECONDS = int(os.getenv("COOLDOWN_SECONDS", "30"))
USE_LLM = os.getenv("USE_LLM", "false").lower() == "true"

if USE_LLM:
    from google import genai
    from google.genai import types
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
else:
    gemini_client = None

_last_trigger = 0
_frigate_token = None

_CAPTIONS = {
    "doorbell": "🔔 Han llamado al timbre",
    "frigate": "🚨 Persona detectada en la puerta",
}


def frigate_login():
    global _frigate_token
    if not FRIGATE_PASSWORD:
        return
    try:
        r = requests.post(
            f"{FRIGATE_URL}/api/login",
            json={"user": FRIGATE_USER, "password": FRIGATE_PASSWORD},
            timeout=5,
        )
        if r.status_code == 200:
            _frigate_token = r.json().get("token")
            log.info("Authenticated with Frigate")
    except Exception as e:
        log.warning(f"Frigate login failed: {e}")


def frigate_get(path):
    headers = {}
    if _frigate_token:
        headers["Authorization"] = f"Bearer {_frigate_token}"
    r = requests.get(f"{FRIGATE_URL}{path}", headers=headers, timeout=10)
    if r.status_code == 401:
        frigate_login()
        if _frigate_token:
            headers["Authorization"] = f"Bearer {_frigate_token}"
            r = requests.get(f"{FRIGATE_URL}{path}", headers=headers, timeout=10)
    r.raise_for_status()
    return r


def fetch_snapshot(event_id=None):
    if event_id:
        try:
            r = frigate_get(f"/api/events/{event_id}/snapshot.jpg")
            return r.content
        except Exception:
            pass
    r = frigate_get(f"/api/{CAMERA_NAME}/latest.jpg")
    return r.content


def analyze_with_gemini(image_bytes, trigger, label=None):
    if trigger == "doorbell":
        prompt = (
            "Someone just rang the doorbell at my front door. "
            "Analyze this image and describe who is there in one or two sentences. "
            "Focus on appearance, clothing, and anything they are carrying."
        )
    else:
        prompt = (
            f"Motion detected at my front door (detected: {label}). "
            "Analyze this image and briefly describe what you see in one or two sentences."
        )
    response = gemini_client.models.generate_content(
        model="gemini-1.5-flash",
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
            prompt,
        ],
    )
    return response.text.strip()


def send_telegram(image_bytes, caption):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    r = requests.post(
        url,
        data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption},
        files={"photo": ("snapshot.jpg", image_bytes, "image/jpeg")},
        timeout=15,
    )
    r.raise_for_status()
    log.info("Telegram notification sent")


def handle_event(trigger, label=None, event_id=None):
    global _last_trigger
    now = time.time()
    if now - _last_trigger < COOLDOWN_SECONDS:
        log.info(f"Cooldown active, skipping {trigger} event")
        return
    _last_trigger = now

    log.info(f"Handling event: trigger={trigger} label={label} event_id={event_id}")
    try:
        image_bytes = fetch_snapshot(event_id)
        if USE_LLM:
            caption = analyze_with_gemini(image_bytes, trigger, label)
            log.info(f"Gemini: {caption}")
        else:
            caption = _CAPTIONS.get(trigger, "🚪 Evento en la puerta")
        send_telegram(image_bytes, caption)
    except Exception as e:
        log.error(f"Pipeline error: {e}")


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        log.info(f"Connected to MQTT broker at {MQTT_HOST}:{MQTT_PORT}")
        client.subscribe("outpost/doorbell")
        client.subscribe("frigate/events")
        log.info("Subscribed to outpost/doorbell and frigate/events")
    else:
        log.error(f"MQTT connection failed rc={rc}")


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
    except Exception:
        return

    if msg.topic == "outpost/doorbell":
        if payload.get("event") == "ring":
            handle_event(trigger="doorbell")

    elif msg.topic == "frigate/events":
        # Only act on new events, not updates or endings
        if payload.get("type") != "new":
            return
        after = payload.get("after", {})
        label = after.get("label", "unknown")
        event_id = after.get("id")
        handle_event(trigger="frigate", label=label, event_id=event_id)


if __name__ == "__main__":
    log.info(f"OpenClaw bridge starting... (USE_LLM={USE_LLM})")
    frigate_login()

    client = mqtt.Client(client_id="openclaw_bridge")
    client.on_connect = on_connect
    client.on_message = on_message

    while True:
        try:
            client.connect(MQTT_HOST, MQTT_PORT, 60)
            client.loop_forever()
        except Exception as e:
            log.error(f"MQTT error: {e} — retrying in 10s")
            time.sleep(10)
