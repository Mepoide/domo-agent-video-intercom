#!/usr/bin/env python3
"""
Smoke test — Node A side (Pi Zero W, 192.168.1.95)
Run this after node_b_listener.py is running on Node B.
Publishes test messages to simulate doorbell events.

Usage:
    python3 node_a_publisher.py

Install deps:
    pip3 install paho-mqtt
"""

import json
import time
import socket
import paho.mqtt.client as mqtt

MQTT_BROKER = "192.168.1.44"
MQTT_PORT = 1883

results = {
    "network_reach": False,
    "mqtt_connect": False,
    "publish_ping": False,
    "publish_doorbell": False,
}


def check_network():
    print("--- Checking network reachability ---")
    try:
        sock = socket.create_connection((MQTT_BROKER, MQTT_PORT), timeout=5)
        sock.close()
        print(f"[OK]  Node B reachable at {MQTT_BROKER}:{MQTT_PORT}")
        results["network_reach"] = True
    except Exception as e:
        print(f"[FAIL] Cannot reach {MQTT_BROKER}:{MQTT_PORT} — {e}")
        print("       Check: is Node B up? Is Mosquitto running?")


def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("[OK]  Connected to MQTT broker on Node B")
        results["mqtt_connect"] = True
    else:
        print(f"[FAIL] MQTT connection refused — rc={rc}")


def publish_tests(client):
    print("\n--- Publishing test messages ---")

    # Basic ping
    res = client.publish("test/ping", "hello-from-nodea", qos=1)
    res.wait_for_publish(timeout=5)
    if res.rc == mqtt.MQTT_ERR_SUCCESS:
        print("[OK]  Published to test/ping")
        results["publish_ping"] = True
    else:
        print(f"[FAIL] test/ping publish failed — rc={res.rc}")

    time.sleep(1)

    # Simulated doorbell event (same payload as doorbell.py)
    payload = json.dumps({"event": "ring"})
    res = client.publish("outpost/doorbell", payload, qos=1)
    res.wait_for_publish(timeout=5)
    if res.rc == mqtt.MQTT_ERR_SUCCESS:
        print(f"[OK]  Published to outpost/doorbell — {payload}")
        results["publish_doorbell"] = True
    else:
        print(f"[FAIL] outpost/doorbell publish failed — rc={res.rc}")


def print_summary():
    print("\n" + "=" * 40)
    print("SMOKE TEST SUMMARY (Node A)")
    print("=" * 40)
    print(f"  Network reach Node B: {'OK' if results['network_reach'] else 'FAIL'}")
    print(f"  MQTT connect:         {'OK' if results['mqtt_connect'] else 'FAIL'}")
    print(f"  Publish test/ping:    {'OK' if results['publish_ping'] else 'FAIL'}")
    print(f"  Publish doorbell:     {'OK' if results['publish_doorbell'] else 'FAIL'}")
    print("=" * 40)
    if all(results.values()):
        print("  ALL CHECKS PASSED — nodes are communicating correctly")
    else:
        print("  SOME CHECKS FAILED — review output above")
    print("=" * 40)


if __name__ == "__main__":
    check_network()
    if not results["network_reach"]:
        print_summary()
        exit(1)

    print("\n--- Connecting to MQTT broker ---")
    try:
        client = mqtt.Client(client_id="smoke_test_publisher", protocol=mqtt.MQTTv5)
    except Exception:
        client = mqtt.Client(client_id="smoke_test_publisher")

    client.on_connect = on_connect

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        time.sleep(2)  # wait for on_connect
    except Exception as e:
        print(f"[FAIL] Cannot connect — {e}")
        print_summary()
        exit(1)

    if results["mqtt_connect"]:
        publish_tests(client)

    time.sleep(1)
    client.loop_stop()
    client.disconnect()
    print_summary()
