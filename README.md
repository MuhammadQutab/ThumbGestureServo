# Hand-Gesture Controlled Servo (Arduino + Python)

Control an SG90 servo with thumb gestures using **MediaPipe Hands + OpenCV** in Python, sending `H` / `L` over serial to an **Arduino UNO**. Two states:
- **OUT (thumb right of palm centre)** → `H` → 180°
- **IN (thumb left of palm centre)** → `L` → 0°

https://github.com/MuhammadQutab/ThumbGestureServo

## Features
- Stable camera pipeline (MSMF/DSHOW) — avoids freezes on laptop webcams
- Palm-centre reference → works with either hand (no handedness dependency)
- Debounce + neutral re-arm → reliable toggling
- Large/resizable OpenCV window (e.g., 1600×900)
- Clean overlay: full landmarks or minimal rails mode




![WhatsApp Image 2025-10-20 at 11 06 18](https://github.com/user-attachments/assets/963db850-1ecb-4363-aad0-75101d70ddf7)





## Demo Link, LinkedIn:

https://www.linkedin.com/posts/muhammadqutab03_arduino-python-opencv-activity-7386505275572215808-iWU1?utm_source=share&utm_medium=member_desktop&rcm=ACoAAEDX9coBoMdRTqxs5ojMW8ScnBWaDJMcSkc



## Requirements
- Python 3.11 (64-bit)
- Arduino UNO + SG90 (positional) servo
- External 5V supply recommended for servo under load

```bash
pip install -r requirements.txt
