# Epic 1: Outdoor Telemetry (Edge Node) Walkthrough

I have successfully implemented the components for Epic 1 inside the `/edge_node_pizero/` directory!

## Changes Made

* **[edge_node_pizero/docker-compose.yml](file:///home/mario/projects/domo-agent-video-intercom/edge_node_pizero/docker-compose.yml)**: Configured the `bluenviron/mediamtx` container. It runs on the host network to prevent routing latencies and mounts `/dev/video0`. It's pre-configured via environment variables to serve both `rpiCamera` or fallback to standard `V4L2`, locked cleanly to **15 FPS** and **640x480 resolution**.
* **[edge_node_pizero/src/doorbell.py](file:///home/mario/projects/domo-agent-video-intercom/edge_node_pizero/src/doorbell.py)**: Created the Python logic using `gpiozero` and `paho.mqtt.client`. It connects to `192.168.1.100` (Node B), listens on GPIO 17 using an internal pull-up resistor, and cleanly publishes `{"event": "ring"}` to `outpost/doorbell`.
* **[edge_node_pizero/requirements.txt](file:///home/mario/projects/domo-agent-video-intercom/edge_node_pizero/requirements.txt)**: Specified `gpiozero` and `paho-mqtt`.

## Validation & Next Steps

Since I do not have direct access to the Raspberry Pi Zero hardware or the physical circuit, **manual verification** is required on your side:

1. Deploy the contents of the `/edge_node_pizero/` directory to the Raspberry Pi Zero (Node A: `192.168.1.50`).
2. Run `docker-compose up -d` inside that directory.
3. Access the stream (e.g., using VLC) via `rtsp://192.168.1.50:8554/cam` to verify the video is live, at 15 FPS, and 640x480 resolution.
4. Install the Python dependencies using `pip install -r requirements.txt`.
5. Run the doorbell script: `python src/doorbell.py`.
6. Press the physical button connected to GPIO pin 17 and ground. You should see logs indicating a successful button press and publication of the message to the MQTT Broker (on `192.168.1.100`), which will be configured in Epic 2.
