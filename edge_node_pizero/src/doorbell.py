import time
import json
import logging
import paho.mqtt.client as mqtt
from gpiozero import Button

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants based on architecture context
MQTT_BROKER = "192.168.1.44"  # Node B IP Address
MQTT_PORT = 1883
MQTT_TOPIC = "outpost/doorbell"
DOORBELL_PIN = 17

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        logging.info(f"Connected successfully to MQTT Broker at {MQTT_BROKER}:{MQTT_PORT}")
    else:
        logging.error(f"Failed to connect to MQTT broker, return code {rc}")

def on_button_pressed():
    """Callback triggered when the physical doorbell button is pressed."""
    logging.info("Doorbell button pressed!")
    # Construct the JSON payload required by the Epic
    payload = json.dumps({"event": "ring"})
    # Publish to MQTT topic
    result = client.publish(MQTT_TOPIC, payload)
    
    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        logging.info(f"Successfully published message to {MQTT_TOPIC}: {payload}")
    else:
        logging.error(f"Failed to publish message. Error code: {result.rc}")

# Initialize MQTT Client (using protocol v5 or v3.1.1 depending on paho-mqtt version, handled gracefully)
try:
    client = mqtt.Client(client_id="edge_node_doorbell", protocol=mqtt.MQTTv5)
except Exception:
    client = mqtt.Client(client_id="edge_node_doorbell")
    
client.on_connect = on_connect

# Connect to the local MQTT broker
logging.info(f"Connecting to MQTT broker at {MQTT_BROKER}...")
try:
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
except Exception as e:
    logging.error(f"Could not connect to MQTT broker: {e}")
    # Proceeding assuming the broker will eventually come online

# Start the MQTT network loop in a non-blocking background thread
client.loop_start()

# Initialize the physical button using gpiozero
# A pull-up resistor is used (pull_up=True), so pressing the button connects it to ground
button = Button(DOORBELL_PIN, pull_up=True, bounce_time=0.1)

# Assign the callback function for when the button is pressed
button.when_pressed = on_button_pressed

logging.info(f"Listening for doorbell presses on GPIO {DOORBELL_PIN}...")

try:
    # Keep the main thread alive indefinitely
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    logging.info("Shutting down externally...")
finally:
    logging.info("Cleaning up...")
    button.close()
    client.loop_stop()
    client.disconnect()
