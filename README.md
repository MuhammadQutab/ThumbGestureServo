# Hand-Gesture Controlled Servo (Arduino + Python)

Control an SG90 servo with thumb gestures using **MediaPipe Hands + OpenCV** in Python, sending `H` / `L` over serial to an **Arduino UNO**. Two states:
- **OUT (thumb right of palm centre)** → `H` → 180°
- **IN (thumb left of palm centre)** → `L` → 0°

https://github.com/<MuhammadQutab>/thumb-gesture-servo

## Features
- Stable camera pipeline (MSMF/DSHOW) — avoids freezes on laptop webcams
- Palm-centre reference → works with either hand (no handedness dependency)
- Debounce + neutral re-arm → reliable toggling
- Large/resizable OpenCV window (e.g., 1600×900)
- Clean overlay: full landmarks or minimal rails mode

## Requirements
- Python 3.11 (64-bit)
- Arduino UNO + SG90 (positional) servo
- External 5V supply recommended for servo under load

```bash
pip install -r requirements.txt
