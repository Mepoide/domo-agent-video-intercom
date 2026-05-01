# 🤖 Antigravity Agent Directives: Domo Agent Project

This document contains the Epics (engineering contracts) required to build the Cognitive Video Intercom. 
**General Directive for all agents:** Before executing any Epic, you must read the `CONTEXT.md` file to fully understand the hardware constraints and network topology.

---

## EPIC 0: Physical Hardware Integration (Fermax ↔ Pi Zero)
**Recommended Assignment:** Human Technician + Agent Alpha review

**Objective:** Wire the Raspberry Pi Zero bidirectionally to the existing Fermax CITYMAX 6201 intercom (ref. 8300, 4+N analogue system, 12Vac).

### Bill of Materials
| Component | Ref | Est. Cost |
|---|---|---|
| Optocoupler PC817 | PC817 | ~€0.50 |
| Resistor 470Ω 1/4W | - | ~€0.10 |
| 5V 1-channel relay module (optocoupled) | SRD-05VDC-SL-C | ~€2.00 |
| Dupont jumper cables | - | ~€1.00 |

### Circuit A — INPUT: Doorbell detection
Detect when someone presses the Fermax street panel button WITHOUT replacing normal intercom operation.

```
Fermax call terminal (+) ──┬── [470Ω] ── PC817 pin 1 (Anode)
                           │
Fermax call terminal (-) ──┴────────── PC817 pin 2 (Cathode)

PC817 pin 4 (Collector) ── GPIO 17 (Pi Zero) + 10kΩ pull-up to 3.3V
PC817 pin 3 (Emitter)  ── GND (Pi Zero)
```

⚠️ SAFETY: The PC817 provides galvanic isolation between the 12Vac Fermax system and the 3.3V GPIO. Never connect Fermax terminals directly to GPIO pins.

### Circuit B — OUTPUT: Door release
Trigger the existing electric door strike via the Fermax opener terminal.

```
GPIO 18 (Pi Zero) ── Relay module IN
Pi Zero 5V        ── Relay module VCC
Pi Zero GND       ── Relay module GND

Relay NO (Normally Open)  ── Fermax opener terminal A
Relay COM (Common)        ── Fermax opener terminal B
```

Pulse duration: 500ms (enough to release the electric strike).
The relay module must be optocoupled to protect the Pi Zero GPIO.

### GPIO Pin Assignment
- GPIO 17 → INPUT, pull-up, doorbell signal from PC817
- GPIO 18 → OUTPUT, active HIGH, triggers relay → door release

---

## EPIC 1: Outdoor Telemetry (Edge Node)
**Recommended Assignment:** Agent Alpha (Edge Systems Engineer)

**Execution Prompt:**
> "Read the `CONTEXT.md` file. Your goal is to set up the video stream and physical event detection on the Raspberry Pi Zero. Create the `/edge_node_pizero/` directory and generate two deliverables:
> 1. An ultra-lightweight `docker-compose.yml` deploying `bluenviron/mediamtx` to expose the physical camera (`/dev/video0`) as a low-latency RTSP stream. Configure it for a moderate resolution (e.g., 800x600) and 15-20 FPS.
> 2. A Python script (`src/doorbell.py`) using the `gpiozero` and `paho-mqtt` libraries. The script must listen to GPIO pin 17 (connected to a physical button with a pull-up resistor). On button press, it must connect to the local MQTT broker (use Node B's IP defined in the context) and publish the message `{"event": "ring"}` to the `outpost/doorbell` topic.
> 3. Add a `requirements.txt` file.
> 4. Make doorbell.py bidirectional: subscribe to the MQTT topic `outpost/open_door`. When the message `{"event": "open"}` is received, activate GPIO 18 HIGH for 500ms then LOW. Log every door release with timestamp. Use gpiozero's OutputDevice for GPIO 18."

---

## EPIC 2: Visual Analysis Matrix (Core Node)
**Recommended Assignment:** Agent Bravo (Edge AI Specialist)

**Execution Prompt:**
> "Read the `CONTEXT.md` file. Your goal is to configure Frigate on the Coral Dev Board. Create the `/core_node_coral/` directory and generate these deliverables:
> 1. A `docker-compose.yml` file that deploys Frigate and Eclipse Mosquitto (MQTT Broker). Ensure Frigate has privileged access or the correct device mappings for the PCIe Edge TPU (`/dev/apex_0`).
> 2. A `config/frigate.yml` file. Strict constraints: Define the detector as `coral` type `edgetpu` pointing to the **PCIe** device. Configure the camera to consume the RTSP stream from Node A. Enable tracking exclusively for the `person` class. Optimize for high performance since the hardware can handle it.
> 3. A basic `config/mosquitto.conf` file that allows anonymous local network connections (port 1883)."

---

## EPIC 3: OpenClaw Bridge (Event → Snapshot → Telegram)
**Recommended Assignment:** Agent Charlie (AI Integration Architect)

**Execution Prompt:**
> "Read the `CONTEXT.md` file. Your goal is to develop the OpenClaw bridge on Node B. The minimum viable contract is that the system works with **no external API keys** — only a Telegram bot token is required. Create the `/cognitive_agent_openclaw/` directory and generate:
> 1. A Python script (`src/openclaw_bridge.py`) that persistently subscribes to the MQTT topics `frigate/events` and `outpost/doorbell`.
> 2. Script logic: When Frigate confirms a person detection or someone rings the doorbell, make an HTTP GET request to Frigate's local REST API to download the event snapshot.
> 3. Base output (no API key needed): send the snapshot to Telegram with a fixed caption based on the trigger:
>    - `outpost/doorbell` → `🔔 Han llamado al timbre`
>    - `frigate/events` (person) → `🚨 Persona detectada en la puerta`
> 4. Optional LLM mode: if the environment variable `USE_LLM=true` is set and a `GEMINI_API_KEY` is provided, replace the fixed caption with a natural language description generated by the Google Gemini API (`gemini-1.5-flash`). The Gemini client must only be initialised when `USE_LLM=true` — the script must not crash at startup if no API key is present.
> 5. Provide a `requirements.txt` (with `google-genai` commented out as optional), an isolated `docker-compose.yml`, and a `.env.example` with `USE_LLM=false` and `GEMINI_API_KEY` commented out by default.
> 6. Add Telegram bot command handler `/abrir`: when the authorised user sends /abrir, publish `{"event": "open"}` to the MQTT topic `outpost/open_door`. Security: only process the command if the `chat_id` matches `TELEGRAM_CHAT_ID` from the environment. Add `TELEGRAM_CHAT_ID` to `.env.example`."