# 🤖 Antigravity Agent Directives: Domo Agent Project

This document contains the Epics (engineering contracts) required to build the Cognitive Video Intercom. 
**General Directive for all agents:** Before executing any Epic, you must read the `CONTEXT.md` file to fully understand the hardware constraints and network topology.

---

## EPIC 1: Outdoor Telemetry (Edge Node)
**Recommended Assignment:** Agent Alpha (Edge Systems Engineer)

**Execution Prompt:**
> "Read the `CONTEXT.md` file. Your goal is to set up the video stream and physical event detection on the Raspberry Pi Zero. Create the `/edge_node_pizero/` directory and generate two deliverables:
> 1. An ultra-lightweight `docker-compose.yml` deploying `bluenviron/mediamtx` to expose the physical camera (`/dev/video0`) as a low-latency RTSP stream. Configure it for a moderate resolution (e.g., 800x600) and 15-20 FPS.
> 2. A Python script (`src/doorbell.py`) using the `gpiozero` and `paho-mqtt` libraries. The script must listen to GPIO pin 17 (connected to a physical button with a pull-up resistor). On button press, it must connect to the local MQTT broker (use Node B's IP defined in the context) and publish the message `{"event": "ring"}` to the `outpost/doorbell` topic.
> 3. Add a `requirements.txt` file."

---

## EPIC 2: Visual Analysis Matrix (Core Node)
**Recommended Assignment:** Agent Bravo (Edge AI Specialist)

**Execution Prompt:**
> "Read the `CONTEXT.md` file. Your goal is to configure Frigate on the Coral Dev Board. Create the `/core_node_coral/` directory and generate these deliverables:
> 1. A `docker-compose.yml` file that deploys Frigate and Eclipse Mosquitto (MQTT Broker). Ensure Frigate has privileged access or the correct device mappings for the PCIe Edge TPU (`/dev/apex_0`).
> 2. A `config/frigate.yml` file. Strict constraints: Define the detector as `coral` type `edgetpu` pointing to the **PCIe** device. Configure the camera to consume the RTSP stream from Node A. Enable tracking exclusively for the `person` class. Optimize for high performance since the hardware can handle it.
> 3. A basic `config/mosquitto.conf` file that allows anonymous local network connections (port 1883)."

---

## EPIC 3: The Cognitive Core (AI Integration)
**Recommended Assignment:** Agent Charlie (AI Integration Architect)

**Execution Prompt:**
> "Read the `CONTEXT.md` file. Your goal is to develop the logical bridge in OpenClaw to connect local events with the Gemini network and the end-user. Create the `/cognitive_agent_openclaw/` directory and generate:
> 1. A Python script (`src/openclaw_bridge.py`) that persistently subscribes to the MQTT topics `frigate/events` and `outpost/doorbell`.
> 2. Script logic: When Frigate confirms a person detection or someone rings the doorbell, the script must make an HTTP GET request to Frigate's local REST API to download the event snapshot (image).
> 3. LLM Integration: Build a dynamic prompt ('Analyze this image of my front door. What is this person doing and are they carrying any equipment or packages?'). Send the image and text to the Google Gemini API (`gemini-1.5-flash` model) using the official `google-genai` SDK.
> 4. Output: Take Gemini's response and send it via a Telegram bot to the user.
> 5. Provide a `requirements.txt`, an isolated `docker-compose.yml` for this service, and a `.env.example` file for the API tokens (Gemini API, Telegram Bot Token)."