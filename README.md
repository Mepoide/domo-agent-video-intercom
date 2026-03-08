# 🚪 Domo Agent: Cognitive Video Intercom

A smart, autonomous video intercom system designed for single-family homes. This project combines the speed of local processing (Edge AI) with the advanced reasoning of cloud-based generative AI.

## 🧠 How it works

Unlike traditional intercoms that only detect "movement", this system understands context. 
1. **Local Detection:** A Raspberry Pi Zero captures the video feed, and a Pi 3 with a Google Coral Edge TPU filters events in real-time (e.g., confirming it's a *person* and not a passing car).
2. **Cognitive Analysis:** The **OpenClaw** agent captures the frame and queries the **Google Gemini API**.
3. **Interaction:** You receive a natural language message (e.g., *"There's a delivery driver with a package at the door"*) and can respond using Text-to-Speech (TTS) directly from Telegram.

## ⚙️ Hardware Architecture

* **Edge Node (Outdoor):** Raspberry Pi Zero W + Camera Module + USB Mic/Speaker. (Raw video capture and actuators).
* **Core Node (Indoor):** Raspberry Pi 3 Model B+ + Google Coral USB Accelerator. (NVR processing with Frigate and orchestration with OpenClaw).

## 📂 Repository Structure

The project is divided into three main domains to facilitate Docker deployment and AI agent management:

```text
domo-agent-video-intercom/
├── agents.md                 # Contracts and Epics for deployment via generative AI
├── CONTEXT.md                # Technical manifest with network topology and static IPs
├── .gitignore                # Rules to ignore sensitive files and credentials
├── README.md                 # Project documentation
│
├── edge_node_pizero/         # [Edge Node] Telemetry and actuators
│   ├── docker-compose.yml    # Deploys MediaMTX (RTSP camera stream)
│   ├── src/
│   │   └── doorbell.py       # Python script for physical doorbell events via MQTT
│   └── requirements.txt      # Python dependencies (gpiozero, paho-mqtt)
│
├── core_node_pi3/            # [Core Node] Frigate NVR and MQTT Broker
│   ├── docker-compose.yml    # Deploys Frigate and Mosquitto broker
│   ├── config/
│   │   ├── frigate.yml       # Google Coral Edge TPU config (limited to 3 FPS)
│   │   └── mosquitto.conf    # MQTT broker configuration
│   └── .env.example          # Template for local credentials
│
└── cognitive_agent_openclaw/ # [Cognitive Node] Logic connecting MQTT, Gemini API, and UI
    ├── docker-compose.yml    # Isolated container for the agent
    ├── src/
    │   └── openclaw_bridge.py# Core logic bridging Frigate events and LLM processing
    ├── requirements.txt      # Python dependencies (google-genai, telegram-bot, etc.)
    └── .env.example          # Template for Gemini API Key and Telegram tokens
