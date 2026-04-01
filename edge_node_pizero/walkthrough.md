# Epic 1: Outdoor Telemetry — Final Walkthrough

## ✅ What Was Accomplished

EPIC 1 is fully deployed on the Raspberry Pi Zero W (Node A, `192.168.1.95`).

## 🏗 Architecture (Final Solution)

The original plan used a single `rpiCamera` source inside MediaMTX. This had to be revised because:
- The official MediaMTX Docker image for **ARMv6** (Pi Zero) does **not** include precompiled libcamera support.
- The newer Raspberry Pi OS (Debian Trixie) uses the modern `libcamera` stack, not the legacy V4L2 `/dev/video0` path.

**Final architecture:**

```
[OV5647 Camera] → rpicam-vid → ffmpeg → RTSP push → MediaMTX (Docker) → VLC/Frigate
```

- **MediaMTX** runs in Docker as a **pure RTSP server** (no camera access).
- **`cam-stream.service`** is a systemd service that runs on the host and captures from the camera using the native `rpicam-vid` binary, pipes through `ffmpeg`, and pushes the H.264 stream to MediaMTX.

## 📁 Files in `edge_node_pizero/`

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Deploys MediaMTX as a lightweight RTSP server on port 8554 |
| `cam-stream.sh` | Captures OV5647 camera at 640x480 15fps and pushes to MediaMTX |
| `cam-stream.service` | Systemd unit to auto-start `cam-stream.sh` on boot |
| `src/doorbell.py` | Listens on GPIO 17 and publishes `{"event": "ring"}` to MQTT |
| `requirements.txt` | Python deps: `gpiozero`, `paho-mqtt` |

## 🚀 Deployment Steps (for reference)

```bash
# 1. Copy files to Pi Zero
scp -r edge_node_pizero pi@192.168.1.95:/home/pi/

# 2. On the Pi: install dependencies
sudo apt-get install -y docker.io docker-compose libcamera-apps ffmpeg netcat-openbsd

# 3. Start MediaMTX
cd edge_node_pizero && sudo docker-compose up -d

# 4. Install camera stream service
sudo cp cam-stream.sh /usr/local/bin/cam-stream.sh
sudo chmod +x /usr/local/bin/cam-stream.sh
sudo cp cam-stream.service /etc/systemd/system/
sudo systemctl enable cam-stream && sudo systemctl start cam-stream

# 5. Install Python doorbell script
pip3 install -r requirements.txt --break-system-packages
nohup python3 src/doorbell.py &
```

## ✔ Verification

- **RTSP stream**: Confirmed working in VLC at `rtsp://192.168.1.95:8554/cam`  
- **Camera sensor**: OV5647 detected by `rpicam-hello --list-cameras`
- **Doorbell script**: Running and listening on GPIO 17. Will connect to MQTT broker once EPIC 2 (Node B) is deployed.

## ⏭ Next Steps — EPIC 2 (Node B — Pi 3)

With Node A streaming live video, the next epic deploys the "brain":
- **Frigate NVR** consuming the RTSP stream with Google Coral TPU (max 3 FPS).
- **Mosquitto MQTT Broker** — this will also unblock the doorbell script on Node A.
