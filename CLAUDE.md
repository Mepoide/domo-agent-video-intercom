# CLAUDE.md — Domo Agent: Cognitive Video Intercom

## Project Overview

A distributed AI-powered video intercom system deployed across two physical nodes on a local LAN. When someone approaches the front door (person detection or doorbell press), the system captures a snapshot, sends it to Google Gemini for analysis, and delivers a natural language description to the user via Telegram.

**Always read `CONTEXT.md` before generating any code or configuration.**

---

## Architecture: Two-Node System

### Node A — Edge Sensor (Outdoor Outpost)
- **Hardware:** Raspberry Pi Zero W (ARMv6, extremely limited CPU/RAM)
- **IP:** `192.168.1.95`
- **Role:** Camera stream only + GPIO doorbell detection
- **Directory:** `edge_node_pizero/`
- **Constraint:** No heavy processing. Offload everything to Node B.

### Node B — Core Processing (Indoor Command)
- **Hardware:** Google Coral Dev Board 4GB (Mendel Linux)
- **IP:** `192.168.1.44`
- **Role:** AI inference, MQTT broker, Frigate NVR, OpenClaw bridge
- **Directory:** `core_node_coral/` and `cognitive_agent_openclaw/`
- **Constraint:** Edge TPU is connected via **PCIe** (`/dev/apex_0`) — never configure it as a USB device.

---

## Network Services

| Service        | Host   | Address                          |
|----------------|--------|----------------------------------|
| RTSP stream    | Node A | `rtsp://192.168.1.95:8554/cam`   |
| MQTT broker    | Node B | `mqtt://192.168.1.44:1883`      |
| Frigate NVR    | Node B | `http://192.168.1.44:5000`      |

**MQTT Topics:**
- `outpost/doorbell` — published by Node A on physical button press
- `frigate/events` — published by Frigate on person detection

---

## Cognitive Pipeline (Data Flow)

1. Node A streams RTSP feed via `mediamtx`
2. Frigate on Node B consumes the stream; PCIe Coral TPU detects `person` class → publishes to `frigate/events`
3. Node A GPIO (pin 17, pull-up) detects doorbell press → publishes `{"event": "ring"}` to `outpost/doorbell`
4. OpenClaw bridge (Node B) subscribes to both MQTT topics; on event, fetches snapshot from Frigate REST API
5. Snapshot + prompt sent to `gemini-1.5-flash` via `google-genai` SDK
6. Gemini response + image forwarded to user via Telegram bot

---

## Directory Structure

```
edge_node_pizero/          # Node A deliverables (Pi Zero W)
  docker-compose.yml       # mediamtx RTSP stream service
  src/doorbell.py          # GPIO + MQTT doorbell script
  requirements.txt

core_node_coral/           # Node B AI/NVR services
  docker-compose.yml       # Frigate + Mosquitto
  config/frigate.yml       # Frigate config (PCIe Coral, person tracking)
  config/mosquitto.conf    # Anonymous LAN MQTT broker

cognitive_agent_openclaw/  # Node B OpenClaw bridge
  src/openclaw_bridge.py   # MQTT → Gemini → Telegram
  docker-compose.yml
  requirements.txt
  .env.example             # GEMINI_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
```

---

## Critical Constraints

- **Pi Zero W is ARMv6** — Docker images must be `linux/arm/v6` compatible. Prefer native `raspbian`/`alpine` images or pre-built ARM binaries. Do not use images that require ARMv7+.
- **Coral TPU is PCIe, not USB** — Frigate detector must use device `/dev/apex_0`, not `/dev/bus/usb`. The `edgetpu` type in frigate.yml must point to the PCIe path.
- **No cloud processing for video** — RTSP stream, Frigate inference, and MQTT all stay on the local LAN. Only the Gemini API call goes out to the internet.
- **Secrets via `.env`** — Never hardcode API keys. All tokens go in `.env` files (excluded from git). Provide `.env.example` templates.

---

## Epics Status

| Epic | Agent   | Description                        | Code     | Hardware deployed |
|------|---------|------------------------------------|----------|-------------------|
| 1    | Alpha   | Edge Node: RTSP stream + doorbell  | Done     | Done — verified   |
| 2    | Bravo   | Core Node: Frigate + Mosquitto     | Done     | Pending (Mendel)  |
| 3    | Charlie | OpenClaw: MQTT → Gemini → Telegram | Pending  | Pending           |

## Hardware Deployment Notes

### Node A — Pi Zero W (Epic 1) — COMPLETE
- Camera: OV5647 via CSI. Stream pipeline: `rpicam-vid → ffmpeg → MediaMTX (Docker)`.
- Docker image `bluenviron/mediamtx` on ARMv6 does NOT support libcamera — stream must be pushed from the host via systemd service (`cam-stream.service`).
- Doorbell: GPIO 17 with internal pull-up (no external resistor needed).
- RTSP stream verified in VLC at `rtsp://192.168.1.95:8554/cam`.

### Node B — Coral Dev Board (Epic 2) — HARDWARE PENDING
- Must flash Mendel Linux using the **flashcard** SD image from coral.ai.
- DIP switches for SD boot: `1=ON, 2=OFF, 3=ON, 4=ON`. After flash: `1=ON, 2=OFF, 3=OFF, 4=OFF`.
- Coral TPU is PCIe (`/dev/apex_0`) — never configure as USB in Frigate.
- User has had issues with faulty MicroSD cards — always use a new card for flashing.
- Full hardware guide in `README.md`.

---

## Key Libraries & Tools

| Component     | Language | Key Libraries                          |
|---------------|----------|----------------------------------------|
| doorbell.py   | Python   | `gpiozero`, `paho-mqtt`               |
| openclaw_bridge.py | Python | `paho-mqtt`, `google-genai`, `python-telegram-bot`, `requests` |
| Frigate       | Docker   | `blakeblackshear/frigate`             |
| RTSP stream   | Docker   | `bluenviron/mediamtx`                 |
| MQTT broker   | Docker   | `eclipse-mosquitto`                   |
