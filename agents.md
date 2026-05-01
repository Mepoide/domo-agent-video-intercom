# 🤖 Antigravity Agent Directives: Domo Agent Project

This document contains the Epics (engineering contracts) required to build the Cognitive Video Intercom. 
**General Directive for all agents:** Before executing any Epic, you must read the `CONTEXT.md` file to fully understand the hardware constraints and network topology.

---

## EPIC 0: Hardware Integration (Physical Layer)
**Recommended Assignment:** Agent Zero (Hardware Integration Engineer)

**Execution Prompt:**
> "Read the `CONTEXT.md` file. Your goal is to document and implement the physical integration between the Raspberry Pi Zero W and the Fermax CITYMAX 6201 analog intercom system (ref. 8300, 4+N system, 12Vac, power supply ref. 4802). The system is bidirectional: the Pi Zero must detect doorbell presses without disrupting the existing intercom, and must be able to trigger the electric door strike on command."

---

### Circuit A — Input: Doorbell Detection (Fermax → Pi Zero)

**Principle:** An optocoupler (PC817) is wired in parallel to the Fermax call terminal. When the visitor presses the button, 12Vac flows through the optocoupler LED, activating the phototransistor, which pulls GPIO 17 LOW. The internal pull-up on the Pi Zero keeps it HIGH at rest. The existing intercom telephone continues to ring normally.

**⚠ Safety:** The PC817 provides galvanic isolation between the 12Vac Fermax circuit and the 3.3V GPIO. **Never connect the Fermax ground (N) to the Pi Zero GND.** Never connect any Fermax terminal directly to a GPIO pin.

```
  FERMAX PLACA                   PC817 OPTOCOUPLER              PI ZERO W
  ─────────────                  ┌──────────────────┐           ──────────
                                 │                  │
  Terminal llamada ──[470Ω]────►│ A (LED+)  C (BJT)│────────── GPIO 17
  (~ 12Vac cuando               │                  │           (INPUT, pull-up 3V3)
   se pulsa el botón)           │                  │
                                 │ K (LED-)  E (BJT)│────────── GND Pi Zero
  Masa Fermax (N) ─────────────►│                  │
                                 └──────────────────┘
  ↑ Esta masa NO se conecta al GND de la Pi Zero.
    El PC817 aísla galvánicamente ambos circuitos.
```

**Comportamiento:** botón pulsado → LED conduce → transistor satura → GPIO 17 = LOW → `doorbell.py` detecta evento y publica a MQTT.

---

### Circuit B — Output: Door Release (Pi Zero → Fermax)

**Principle:** A 5V relay module (optocoupled) is driven by GPIO 18. When the relay coil is energised, the Normally-Open (NO) contact closes, shorting the Fermax door-release terminals and triggering the electric strike. The pulse lasts 500 ms — enough to unlatch the door.

**⚠ Safety:** The relay module must be optocoupled (most 1-channel 5V modules from reputable suppliers are). Verify the relay contact is rated for AC loads. Never bridge relay COM and NO before connecting to the Fermax — check with a multimeter first that NO is open at rest.

```
  PI ZERO W                      MÓDULO RELÉ 5V 1CH             FERMAX PLACA
  ─────────                      ┌──────────────────┐           ──────────
                                 │                  │
  GPIO 18 (OUTPUT) ────────────►│ IN         NO    │────────── Terminal abrepuertas
                                 │                  │
  5V Pi Zero ──────────────────►│ VCC        COM   │────────── Masa Fermax (N)
                                 │                  │
  GND Pi Zero ─────────────────►│ GND              │
                                 └──────────────────┘
  Pulso: GPIO 18 HIGH (500ms) → relé cierra → cerradura abre → GPIO 18 LOW
```

---

### Component List

| # | Componente | Referencia / Descripción | Precio aprox. |
|---|-----------|--------------------------|---------------|
| 1 | Optoacoplador | PC817 (DIP-4) | ~0.10 €/ud |
| 2 | Resistencia | 470 Ω, 1/4 W | ~0.02 €/ud |
| 3 | Módulo relé | 5V, 1 canal, optoacoplado | ~2–3 € |
| 4 | Cable Dupont | Hembra-hembra, 20 cm | ~0.50 € (pack) |
| 5 | Cable fino | Para empalmar en bornas Fermax | disponible |

**Total estimado: < 5 €** (excluyendo cables de repuesto y Pi Zero W ya instalada)

---

### GPIO Summary — Node A (Pi Zero W)

| Pin | Dirección | Función |
|-----|-----------|---------|
| GPIO 17 | INPUT (pull-up) | Detección timbre via PC817 |
| GPIO 18 | OUTPUT | Control relé → abrepuertas Fermax |

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
> 5. Provide a `requirements.txt` (with `google-genai` commented out as optional), an isolated `docker-compose.yml`, and a `.env.example` with `USE_LLM=false` and `GEMINI_API_KEY` commented out by default."