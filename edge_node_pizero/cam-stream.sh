#!/bin/bash
# Camera capture service: captures from libcamera and pushes RTSP to MediaMTX
# This runs on the Pi Zero host (not in Docker) to avoid ARMv6 compatibility issues.
#
# Install service:
#   sudo cp cam-stream.sh /usr/local/bin/cam-stream.sh
#   sudo chmod +x /usr/local/bin/cam-stream.sh
#   sudo cp cam-stream.service /etc/systemd/system/
#   sudo systemctl enable cam-stream && sudo systemctl start cam-stream

# Wait for MediaMTX RTSP server to become available
while ! nc -z localhost 8554; do sleep 1; done

# Capture from the OV5647 camera module at 640x480 15fps and push to MediaMTX
rpicam-vid \
  --width 640 \
  --height 480 \
  --framerate 15 \
  --codec h264 \
  --inline \
  --nopreview \
  -t 0 \
  -o - | \
ffmpeg \
  -re \
  -i pipe:0 \
  -c:v copy \
  -f rtsp \
  -rtsp_transport tcp \
  rtsp://127.0.0.1:8554/cam
