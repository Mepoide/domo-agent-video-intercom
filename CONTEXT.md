# 🌍 Project Manifest & Architecture Context

This document serves as the ground truth for all engineering agents working on the "Domo Agent: Cognitive Video Intercom" project. **Agents must read and adhere to these constraints before generating any code or configuration.**

## 1. Hardware Constraints & Deployment Nodes

* **Node A (Edge Sensor - Outdoor Outpost):**
    * **Hardware:** Raspberry Pi Zero W.
    * **Capabilities:** Extremely limited CPU/RAM. Only responsible for streaming raw camera feed and reading physical GPIO states (doorbell button).
    * **IP Address:** `192.168.1.50` *(Update before deployment)*.

* **Node B (Core Processing - Indoor Command):**
    * **Hardware:** Raspberry Pi 3 Model B+ with a Google Coral USB Accelerator.
    * **Constraints:** The Pi 3 relies on **USB 2.0 ports**. This is a massive bottleneck for the Coral TPU. Camera streams analyzed by Frigate MUST be limited to a maximum of 3 FPS and low resolution (e.g., 640x480) to prevent crashing the USB bus.
    * **IP Address:** `192.168.1.100` *(Update before deployment)*.

## 2. Network Topology & Services

All services communicate over the local LAN to ensure low latency.

* **RTSP Video Stream:** Hosted on Node A via `mediamtx`. Accessible at `rtsp://192.168.1.50:8554/cam`.
* **MQTT Broker:** Hosted on Node B via Eclipse Mosquitto. Accessible at `mqtt://192.168.1.100:1883`. 
    * *Topics:* `outpost/doorbell` (Node A publishes), `frigate/events` (Frigate publishes).

## 3. The Cognitive Pipeline (Data Flow)

1.  **Telemetry:** Node A streams the live RTSP feed to Node B.
2.  **Edge AI Filter:** Frigate (Node B) consumes the RTSP stream, uses the Coral TPU to detect the `person` class at a maximum of 3 FPS, and publishes an event to the local MQTT broker.
3.  **Physical Trigger:** Node A reads a physical doorbell button press (GPIO) and publishes the event to MQTT.
4.  **Cognitive Synthesis:** OpenClaw (Node B) subscribes to MQTT. Upon receiving a person or doorbell event, it fetches the snapshot from Frigate's local REST API, constructs a dynamic prompt, and calls the Google Gemini API.
5.  **Output:** OpenClaw sends the LLM's natural language analysis and the image directly to the user's mobile UI (Telegram).