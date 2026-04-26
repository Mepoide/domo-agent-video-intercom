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

smoke_test/                # Inter-node connectivity validation
  node_b_listener.py       # Run on Node B — subscribes to all topics, checks Frigate API
  node_a_publisher.py      # Run on Node A — publishes test messages, reports results
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
| 2    | Bravo   | Core Node: Frigate + Mosquitto     | Done     | Done — verified   |
| 3    | Charlie | OpenClaw: MQTT → Gemini → Telegram | Done     | Pending deploy    |

## Epic 3 — Pendiente de deploy

Antes de arrancar `cognitive_agent_openclaw` en Node B se necesitan:
1. Crear `.env` a partir de `.env.example` con las credenciales reales
2. `GEMINI_API_KEY` — Google AI Studio
3. `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` — @BotFather / @userinfobot
4. `FRIGATE_PASSWORD` — `sudo docker logs frigate 2>&1 | grep -A2 "default user"`
5. Copiar directorio a Node B y lanzar: `sudo docker compose up -d`

## Inter-Node Comms — Verified

MQTT communication between Node A and Node B verified via smoke tests (`smoke_test/`):
- Node A → Node B TCP reachability: OK
- Node A MQTT publish to `outpost/doorbell`: OK
- Node B MQTT broker receives messages: OK
- SSH key-based access configured on both nodes (key: `~/.ssh/id_ed25519`)
- Node B Python: 3.7 — use `paho-mqtt<2.0`

## Hardware Deployment Notes

### Node A — Pi Zero W (Epic 1) — COMPLETE
- Camera: OV5647 via CSI. Stream pipeline: `rpicam-vid → ffmpeg → MediaMTX (Docker)`.
- Docker image `bluenviron/mediamtx` on ARMv6 does NOT support libcamera — stream must be pushed from the host via systemd service (`cam-stream.service`).
- Doorbell: GPIO 17 with internal pull-up (no external resistor needed).
- RTSP stream verified in VLC at `rtsp://192.168.1.95:8554/cam`.

### Node B — Coral Dev Board (Epic 2) — COMPLETE
- Mendel Linux installed, SSH working, IP `192.168.1.44`.
- Docker CE 26.1.4 installed (not docker.io — too old on Mendel).
- Frigate 0.17 + Mosquitto running. Coral PCIe TPU detected (`device: pci`).
- Frigate admin password auto-generated on first run, saved to `/home/mendel/.env.local`.
- Critical config lessons (see README for full table):
  - `network_mode: host` — Mendel kernel has no `net_cls` cgroup
  - Config file must be `config.yml` (not `frigate.yml`)
  - MQTT host must be `localhost` (no Docker DNS with host networking)
  - EdgeTPU device string must be `pci` — `/dev/apex_0` causes delegate failure
  - Do NOT mount host libedgetpu into container — ABI mismatch with Frigate's tflite_runtime

---

## Key Libraries & Tools

| Component     | Language | Key Libraries                          |
|---------------|----------|----------------------------------------|
| doorbell.py   | Python   | `gpiozero`, `paho-mqtt`               |
| openclaw_bridge.py | Python | `paho-mqtt`, `google-genai`, `python-telegram-bot`, `requests` |
| Frigate       | Docker   | `blakeblackshear/frigate`             |
| RTSP stream   | Docker   | `bluenviron/mediamtx`                 |
| MQTT broker   | Docker   | `eclipse-mosquitto`                   |
