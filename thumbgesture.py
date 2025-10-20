# --- Windows camera stability flags (keep!) ---
import os
os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"
os.environ["OPENCV_LOG_LEVEL"] = "SILENT"

import time
import cv2
import serial
import mediapipe as mp

# ===== SETTINGS ==============================================================
PORT = "COM7"          # <-- set your Arduino COM port
BAUD = 115200
CAM_INDEX = 0

FRAME_W = 480          # 424–640 recommended; increase if your CPU handles it
FPS_REQ  = 24
X_THRESH_FRAC = 0.14   # thumb distance from palm centre (as % of width)
COOLDOWN_S    = 0.25   # min time between armed sends

DRAW = True            # master switch (False = fastest)
DRAW_MODE = "full"     # "full" = 21 pts + connections (like your screenshot)
                       # "minimal" = only rails + 2 dots (palm centre + thumb tip)
# ============================================================================

def open_serial(port, baud):
    try:
        ser = serial.Serial(port, baud, timeout=0.1, write_timeout=0.1)
        time.sleep(1.5)
        ser.reset_input_buffer()
        print(f"[SERIAL] Opened {port} @ {baud}")
        return ser
    except Exception as e:
        print(f"[WARN] Serial open failed: {e} (continuing without serial)")
        return None

def open_cam(index):
    # Try MSMF first, fallback to DSHOW
    cap = cv2.VideoCapture(index, cv2.CAP_MSMF)
    if not cap.isOpened():
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        raise RuntimeError(f"Camera index {index} could not be opened.")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_W)
    cap.set(cv2.CAP_PROP_FPS, FPS_REQ)
    return cap

arduino = open_serial(PORT, BAUD)
cap = open_cam(CAM_INDEX)

mp_hands  = mp.solutions.hands
mp_draw   = mp.solutions.drawing_utils
mp_styles = mp.solutions.drawing_styles

hands = mp_hands.Hands(
    model_complexity=0,          # light model = faster & stable
    max_num_hands=1,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.6
)

# --- simple state machine: must pass through NEUTRAL between commands ---
ARMED_NEXT = "ANY"    # "H", "L", or "ANY"; after sending we require neutral
last_send_time = 0.0

def send_cmd(ch):
    global last_send_time, ARMED_NEXT
    if arduino:
        try: arduino.write(ch.encode())
        except Exception as e: print(f"[SERIAL] write failed: {e}")
    print(f"Sent {ch} ({'180°' if ch=='H' else '0°'})")
    last_send_time = time.time()
    ARMED_NEXT = "NONE"    # disarm until neutral band is reached

print("Ready. Thumb right of palm → H(180°). Thumb left → L(0°). H/L keys work too. Q quits.")

try:
    while True:
        ok, frame = cap.read()
        if not ok:
            time.sleep(0.005)
            continue

        frame = cv2.flip(frame, 1)
        h0, w0 = frame.shape[:2]
        if w0 != FRAME_W:
            scale = FRAME_W / float(w0)
            frame = cv2.resize(frame, (FRAME_W, int(h0 * scale)), interpolation=cv2.INTER_AREA)
        h, w = frame.shape[:2]

        # Inference
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        res = hands.process(rgb)
        rgb.flags.writeable = True

        status, color = "Show hand", (180,180,180)

        if res.multi_hand_landmarks:
            hlms = res.multi_hand_landmarks[0]

            # Palm centre = average of wrist + MCPs (stable reference for either hand)
            PALM_IDXS = [0, 5, 9, 13, 17]
            cx = sum(hlms.landmark[i].x for i in PALM_IDXS) / len(PALM_IDXS)
            cy = sum(hlms.landmark[i].y for i in PALM_IDXS) / len(PALM_IDXS)
            x_palm  = cx * w
            y_palm  = cy * h
            x_thumb = hlms.landmark[4].x * w
            y_thumb = hlms.landmark[4].y * h

            delta  = x_thumb - x_palm
            thresh = X_THRESH_FRAC * w

            # re-arm only after the thumb returns near palm
            now = time.time()
            in_neutral = abs(delta) < (0.6 * thresh)
            if ARMED_NEXT == "NONE" and in_neutral:
                ARMED_NEXT = "ANY"
            can_send = (now - last_send_time) >= COOLDOWN_S and ARMED_NEXT in ("ANY", "H", "L")

            if delta > thresh:
                status, color = "OUT → H (180°)", (0,200,0)
                if can_send and ARMED_NEXT in ("ANY","H"):
                    send_cmd('H')
            elif delta < -thresh:
                status, color = "IN → L (0°)", (0,165,255)
                if can_send and ARMED_NEXT in ("ANY","L"):
                    send_cmd('L')
            else:
                status, color = "Neutral", (200,200,0)

            # ---------------- Drawing (toggle modes) ----------------
            if DRAW:
                if DRAW_MODE == "full":
                    mp_draw.draw_landmarks(
                        frame, hlms, mp_hands.HAND_CONNECTIONS,
                        mp_styles.get_default_hand_landmarks_style(),
                        mp_styles.get_default_hand_connections_style()
                    )
                else:  # minimal
                    cv2.circle(frame, (int(x_palm),  int(y_palm)),  5, (255,255,255), -1)
                    cv2.circle(frame, (int(x_thumb), int(y_thumb)), 5, (255,255,255), -1)

                # rails around palm centre
                x1, x2 = int(x_palm - thresh), int(x_palm + thresh)
                cv2.line(frame, (x1, 0), (x1, h), (180,180,180), 1)
                cv2.line(frame, (x2, 0), (x2, h), (180,180,180), 1)

        # Keyboard overrides
        k = cv2.waitKey(1) & 0xFF
        if k == ord('q'):
            break
        elif k in (ord('h'), ord('H')):
            send_cmd('H'); ARMED_NEXT = "NONE"
        elif k in (ord('l'), ord('L')):
            send_cmd('L'); ARMED_NEXT = "NONE"
        elif k == ord('m'):
            # quick toggle between full/minimal draw at runtime
            DRAW_MODE = "minimal" if DRAW_MODE == "full" else "full"
            print(f"[DRAW] mode → {DRAW_MODE}")

        if DRAW:
            cv2.putText(frame, status, (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2, cv2.LINE_AA)
            cv2.putText(
                frame,
                "Q quit | H/L keys send | 'm' toggles full/minimal draw",
                (10, h-10), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180,180,180), 1
            )
            cv2.imshow("Thumb Servo Control (Full Hand)", frame)

finally:
    try: hands.close()
    except: pass
    cap.release()
    if arduino:
        try: arduino.close()
        except: pass
    cv2.destroyAllWindows()