import time
import json
import logging
import threading
import paho.mqtt.client as mqtt
from gpiozero import Button, OutputDevice

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

MQTT_BROKER = "192.168.1.44"  # Node B IP
MQTT_PORT = 1883
DOORBELL_TOPIC = "outpost/doorbell"
OPEN_DOOR_TOPIC = "outpost/open_door"
DOORBELL_PIN = 17   # INPUT  — PC817 optocoupler output
RELAY_PIN = 18      # OUTPUT — 5V relay module → Fermax abrepuertas
RELAY_PULSE_SECONDS = 0.5


def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        logging.info(f"Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
        client.subscribe(OPEN_DOOR_TOPIC)
        logging.info(f"Subscribed to {OPEN_DOOR_TOPIC}")
    else:
        logging.error(f"Failed to connect to MQTT broker, return code {rc}")


def on_button_pressed():
    payload = json.dumps({"event": "ring"})
    result = client.publish(DOORBELL_TOPIC, payload)
    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        logging.info(f"Doorbell published to {DOORBELL_TOPIC}")
    else:
        logging.error(f"Failed to publish doorbell event, error code: {result.rc}")


def pulse_relay():
    relay.on()
    logging.info(f"Relay ON — activating door release")
    time.sleep(RELAY_PULSE_SECONDS)
    relay.off()
    logging.info("Relay OFF — door release complete")


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
    except Exception:
        return
    if msg.topic == OPEN_DOOR_TOPIC and payload.get("event") == "open":
        logging.info("Open door command received — activating relay")
        threading.Thread(target=pulse_relay, daemon=True).start()


try:
    client = mqtt.Client(client_id="edge_node_doorbell", protocol=mqtt.MQTTv5)
except Exception:
    client = mqtt.Client(client_id="edge_node_doorbell")

client.on_connect = on_connect
client.on_message = on_message

logging.info(f"Connecting to MQTT broker at {MQTT_BROKER}...")
try:
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
except Exception as e:
    logging.error(f"Could not connect to MQTT broker: {e}")

client.loop_start()

relay = OutputDevice(RELAY_PIN, initial_value=False)
button = Button(DOORBELL_PIN, pull_up=True, bounce_time=0.1)
button.when_pressed = on_button_pressed

logging.info(f"Ready — doorbell on GPIO {DOORBELL_PIN}, relay on GPIO {RELAY_PIN}")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    logging.info("Shutting down...")
finally:
    logging.info("Cleaning up...")
    button.close()
    relay.close()
    client.loop_stop()
    client.disconnect()
