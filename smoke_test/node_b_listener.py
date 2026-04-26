#!/usr/bin/env python3
"""
Smoke test — Node B side (Coral Dev Board, 192.168.1.44)
Run this first. It subscribes to all expected topics and prints what arrives.

Usage:
    python3 node_b_listener.py

Install deps:
    pip3 install paho-mqtt requests
"""

import json
import time
import requests
import paho.mqtt.client as mqtt

MQTT_HOST = "localhost"
MQTT_PORT = 1883
FRIGATE_URL = "http://localhost:5000"

TOPICS = [
    "outpost/doorbell",
    "frigate/events",
    "test/ping",
]

results = {
    "mqtt_broker": False,
    "frigate_api": False,
    "received_topics": set(),
}


def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("[OK]  Connected to local MQTT broker")
        results["mqtt_broker"] = True
        for topic in TOPICS:
            client.subscribe(topic)
            print(f"      Subscribed to: {topic}")
    else:
        print(f"[FAIL] MQTT connection refused — rc={rc}")


def on_message(client, userdata, msg):
    topic = msg.topic
    try:
        payload = json.loads(msg.payload.decode())
    except Exception:
        payload = msg.payload.decode()

    results["received_topics"].add(topic)
    print(f"\n[MSG] Topic: {topic}")
    print(f"      Payload: {payload}")


def check_frigate():
    print("\n--- Checking Frigate API ---")
    try:
        r = requests.get(f"{FRIGATE_URL}/api/version", timeout=5)
        if r.status_code == 200:
            print(f"[OK]  Frigate reachable — version: {r.json().get('version', '?')}")
            results["frigate_api"] = True
        else:
            print(f"[FAIL] Frigate returned HTTP {r.status_code}")
    except Exception as e:
        print(f"[FAIL] Frigate not reachable — {e}")


def print_summary():
    print("\n" + "=" * 40)
    print("SMOKE TEST SUMMARY (Node B)")
    print("=" * 40)
    print(f"  MQTT broker up:    {'OK' if results['mqtt_broker'] else 'FAIL'}")
    print(f"  Frigate API up:    {'OK' if results['frigate_api'] else 'FAIL'}")
    received = results["received_topics"]
    if received:
        print(f"  Topics received:   {', '.join(received)}")
    else:
        print("  Topics received:   none yet (run node_a_publisher.py on Node A)")
    print("=" * 40)


if __name__ == "__main__":
    check_frigate()

    print("\n--- Starting MQTT listener ---")
    try:
        client = mqtt.Client(client_id="smoke_test_listener", protocol=mqtt.MQTTv5)
    except Exception:
        client = mqtt.Client(client_id="smoke_test_listener")

    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(MQTT_HOST, MQTT_PORT, 60)
    except Exception as e:
        print(f"[FAIL] Cannot connect to MQTT broker at {MQTT_HOST}:{MQTT_PORT} — {e}")
        print("       Is Mosquitto running? Check: docker ps")
        exit(1)

    print("Waiting for messages (Ctrl+C to stop and show summary)...")
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        pass
    finally:
        client.disconnect()
        print_summary()
