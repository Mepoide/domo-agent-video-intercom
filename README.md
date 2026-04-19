# Domo Agent: Cognitive Video Intercom

A smart, autonomous video intercom system designed for single-family homes. Combines local Edge AI processing with cloud-based generative AI.

## How it works

1. **Local Detection:** A Raspberry Pi Zero W streams the video feed. A Google Coral Dev Board with a native PCIe Edge TPU runs Frigate NVR to detect persons in real-time.
2. **Cognitive Analysis:** The OpenClaw agent captures the snapshot and queries the Google Gemini API.
3. **Notification:** You receive a natural language message (e.g., *"There's a delivery driver with a package at the door"*) via Telegram.

---

## Hardware Architecture

| Node | Device | Role | IP |
|------|--------|------|----|
| Node A — Edge Sensor | Raspberry Pi Zero W + OV5647 Camera | RTSP stream + GPIO doorbell | `192.168.1.95` |
| Node B — Core Processing | Google Coral Dev Board 4GB | Frigate NVR + MQTT + OpenClaw | `192.168.1.44` |

---

## Hardware Setup Guide

### Node A — Raspberry Pi Zero W

#### Physical wiring
- **Camera:** OV5647 module connected via CSI ribbon cable.
- **Doorbell button:** Connected between **GPIO 17** and **GND**. The script uses an internal pull-up resistor — no external resistor needed.

#### OS & dependencies
```bash
# Raspberry Pi OS (Debian Trixie, 64-bit lite recommended)
# After first boot:
sudo apt-get update
sudo apt-get install -y docker.io docker-compose libcamera-apps ffmpeg netcat-openbsd
```

#### Architecture note
The official MediaMTX Docker image for ARMv6 does **not** include precompiled libcamera support. The final working architecture is:

```
[OV5647 Camera] → rpicam-vid → ffmpeg → RTSP push → MediaMTX (Docker) → Frigate
```

MediaMTX runs in Docker as a pure RTSP server. A systemd service on the host captures from the camera and pushes the stream into the container.

#### Deployment
```bash
# 1. Copy files to the Pi Zero
scp -r edge_node_pizero pi@192.168.1.95:/home/pi/

# 2. Start MediaMTX container
cd /home/pi/edge_node_pizero
sudo docker-compose up -d

# 3. Install and enable the camera stream systemd service
sudo cp cam-stream.sh /usr/local/bin/cam-stream.sh
sudo chmod +x /usr/local/bin/cam-stream.sh
sudo cp cam-stream.service /etc/systemd/system/
sudo systemctl enable cam-stream
sudo systemctl start cam-stream

# 4. Install Python dependencies and run doorbell script
pip3 install -r requirements.txt --break-system-packages
nohup python3 src/doorbell.py &
```

#### Verification
- Stream: open `rtsp://192.168.1.95:8554/cam` in VLC — should show 640x480 at 15 FPS.
- Camera detected: `rpicam-hello --list-cameras` should list the OV5647.
- Doorbell: press the button on GPIO 17, check logs for MQTT publish.

**Status: Epic 1 complete and verified.**

---

### Node B — Google Coral Dev Board 4GB

#### Flashing Mendel Linux (first-time setup)

**Requirements:** MicroSD card (8GB minimum, tested with a new card — used/faulty cards cause read errors).

**Step 1 — Prepare the MicroSD**

Download the **flashcard** image from the official Coral software page and flash it to the MicroSD using Raspberry Pi Imager or BalenaEtcher.

**Step 2 — Set DIP switches to SD Card boot mode**

The board has 4 DIP switches near the GPIO header. Set them as follows before inserting power:

```
Switch 1: ON  (up)
Switch 2: OFF (down)
Switch 3: ON  (up)
Switch 4: ON  (up)
```

**Step 3 — Flash the board**

1. Insert the MicroSD into the Coral Dev Board.
2. Connect power via the USB-C **PWR** port (not the OTG port).
3. The board will boot from the SD card and automatically flash Mendel Linux to the internal eMMC.
4. Wait 5–10 minutes. The board will power itself off when done (fan stops, red LED off).

**Step 4 — Restore normal boot mode**

1. Disconnect power.
2. Remove the MicroSD.
3. Set DIP switches back to eMMC boot mode:

```
Switch 1: ON  (up)
Switch 2: OFF (down)
Switch 3: OFF (down)
Switch 4: OFF (down)
```

4. Reconnect power. The board boots Mendel Linux from internal storage.

#### Connecting to the board

Install MDT (Mendel Development Tool) on your PC:
```bash
pip3 install --user mendel-development-tool
```

Connect the board via USB-C OTG port to your PC, then:
```bash
mdt shell
# Logs in as user: mendel
```

#### Deployment (after Mendel is running)
```bash
# Copy files from dev machine
scp -r core_node_coral mendel@192.168.1.44:/home/mendel/

# On the Coral board
cd /home/mendel/core_node_coral
sudo docker-compose up -d
```

**Status: Mendel setup in progress.**

---

## Repository Structure

```
domo-agent-video-intercom/
├── agents.md                      # Epics and agent directives
├── CONTEXT.md                     # Technical manifest (hardware, IPs, topology)
├── CLAUDE.md                      # Claude Code instructions
│
├── edge_node_pizero/              # Node A — Pi Zero W
│   ├── docker-compose.yml         # MediaMTX RTSP server
│   ├── cam-stream.sh              # rpicam-vid → ffmpeg → MediaMTX push
│   ├── cam-stream.service         # systemd unit for auto-start on boot
│   ├── src/doorbell.py            # GPIO 17 → MQTT publisher
│   └── requirements.txt
│
├── core_node_coral/               # Node B — Coral Dev Board
│   ├── docker-compose.yml         # Frigate + Mosquitto
│   ├── config/frigate.yml         # PCIe Coral TPU config, person tracking
│   └── config/mosquitto.conf      # Anonymous LAN MQTT broker
│
└── cognitive_agent_openclaw/      # Node B — OpenClaw AI Bridge
    ├── src/openclaw_bridge.py     # MQTT → Gemini → Telegram
    ├── docker-compose.yml
    ├── requirements.txt
    └── .env.example               # GEMINI_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
```

---

## Epic Status

| Epic | Agent | Description | Status |
|------|-------|-------------|--------|
| 1 | Alpha | Edge Node: RTSP stream + GPIO doorbell (Pi Zero W) | Complete |
| 2 | Bravo | Core Node: Frigate + Mosquitto (Coral Dev Board) | Code ready, hardware pending |
| 3 | Charlie | OpenClaw: MQTT → Gemini → Telegram | Pending |
