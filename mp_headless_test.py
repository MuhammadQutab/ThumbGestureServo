# --- Windows camera stability flags ---
import os
os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"
os.environ["OPENCV_LOG_LEVEL"] = "SILENT"

import time
import cv2
import serial
import mediapipe as mp

# ===== SETTINGS =====
PORT = "COM7"          # <— change to your Arduino COM port
BAUD = 115200
CAM_INDEX = 0

FRAME_W = 480
FPS_REQ  = 24
X_THRESH_FRAC = 0.14
COOLDOWN_S    = 0.25

DRAW = True
DRAW_MODE = "full"     # "full" or "minimal"
WIN_NAME = "Thumb Servo Control (2-State)"

# ===== Helpers =====
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
    cap = cv2.VideoCapture(index, cv2.CAP_MSMF)
    if not cap.isOpened():
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        raise RuntimeError(f"Camera {index} could not be opened.")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_W)
    cap.set(cv2.CAP_PROP_FPS, FPS_REQ)
    return cap

def send_cmd(ser, ch):
    if ser:
        try: ser.write(ch.encode())
        except Exception as e: print(f"[SERIAL] write failed: {e}")
    print(f"Sent {ch} ({'180°' if ch=='H' else '0°'})")

# ===== Init =====
arduino = open_serial(PORT, BAUD)
cap = open_cam(CAM_INDEX)

mp_hands  = mp.solutions.hands
mp_draw   = mp.solutions.drawing_utils
mp_styles = mp.solutions.drawing_styles

hands = mp_hands.Hands(
    model_complexity=0,
    max_num_hands=1,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.6
)

# Custom large window
cv2.namedWindow(WIN_NAME, cv2.WINDOW_NORMAL)
cv2.resizeWindow(WIN_NAME, 1600, 900)   # <— change size here
cv2.moveWindow(WIN_NAME, 50, 50)        # <— move window position (optional)

# State machine
ARMED_NEXT = "ANY"
last_send_time = 0.0

print("2-State: OUT→H (180°), IN→L (0°). Keys: H/L send, M toggle draw, Q quit.")

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

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        res = hands.process(rgb)
        rgb.flags.writeable = True

        status, color = "Show hand", (180,180,180)

        if res.multi_hand_landmarks:
            hlms = res.multi_hand_landmarks[0]

            PALM_IDXS = [0, 5, 9, 13, 17]
            cx = sum(hlms.landmark[i].x for i in PALM_IDXS) / len(PALM_IDXS)
            cy = sum(hlms.landmark[i].y for i in PALM_IDXS) / len(PALM_IDXS)
            x_palm, y_palm = cx * w, cy * h
            x_thumb = hlms.landmark[4].x * w

            delta  = x_thumb - x_palm
            thresh = X_THRESH_FRAC * w
            now = time.time()

            in_neutral = abs(delta) < (0.6 * thresh)
            if ARMED_NEXT == "NONE" and in_neutral:
                ARMED_NEXT = "ANY"
            can_send = (now - last_send_time) >= COOLDOWN_S and ARMED_NEXT in ("ANY","H","L")

            if delta > thresh:
                status, color = "OUT → H (180°)", (0,200,0)
                if can_send and ARMED_NEXT in ("ANY","H"):
                    send_cmd(arduino, 'H')
                    last_send_time = now
                    ARMED_NEXT = "NONE"
            elif delta < -thresh:
                status, color = "IN → L (0°)", (0,165,255)
                if can_send and ARMED_NEXT in ("ANY","L"):
                    send_cmd(arduino, 'L')
                    last_send_time = now
                    ARMED_NEXT = "NONE"
            else:
                status, color = "Neutral", (200,200,0)

            # Draw landmarks
            if DRAW:
                if DRAW_MODE == "full":
                    mp_draw.draw_landmarks(
                        frame, hlms, mp_hands.HAND_CONNECTIONS,
                        mp_styles.get_default_hand_landmarks_style(),
                        mp_styles.get_default_hand_connections_style()
                    )
                else:
                    cv2.circle(frame, (int(x_palm), int(y_palm)), 5, (255,255,255), -1)
                    cv2.circle(frame, (int(x_thumb), int(hlms.landmark[4].y * h)), 5, (255,255,255), -1)

                # rails
                x1, x2 = int(x_palm - thresh), int(x_palm + thresh)
                cv2.line(frame, (x1, 0), (x1, h), (180,180,180), 1)
                cv2.line(frame, (x2, 0), (x2, h), (180,180,180), 1)

        # Keyboard
        k = cv2.waitKey(1) & 0xFF
        if k == ord('q'):
            break
        elif k in (ord('h'), ord('H')):
            send_cmd(arduino, 'H'); last_send_time = time.time(); ARMED_NEXT = "NONE"
        elif k in (ord('l'), ord('L')):
            send_cmd(arduino, 'L'); last_send_time = time.time(); ARMED_NEXT = "NONE"
        elif k == ord('m'):
            DRAW_MODE = "minimal" if DRAW_MODE == "full" else "full"
            print(f"[DRAW] mode → {DRAW_MODE}")

        if DRAW:
            cv2.putText(frame, status, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2, cv2.LINE_AA)
            cv2.putText(frame, "H/L keys | 'm' toggle draw | Q quit",
                        (10, h-10), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180,180,180), 1)
            cv2.imshow(WIN_NAME, frame)

finally:
    try: hands.close()
    except: pass
    cap.release()
    if arduino:
        try: arduino.close()
        except: pass
    cv2.destroyAllWindows()