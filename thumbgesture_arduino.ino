#include <Servo.h>

Servo s;

const int SERVO_PIN = 9;

// Ends (adjust if your horn hits limits early)
const int ANGLE_MIN = 0;
const int ANGLE_MAX = 180;

// Motion tuning
const uint8_t STEP_DEG      = 2;    // degrees per update (bigger = faster)
const uint16_t STEP_PERIOD  = 12;   // ms between updates (smaller = faster)

// State
volatile int targetAngle = 90;
int currentAngle         = 90;
unsigned long lastStepMs = 0;

// ---------- Helpers ----------
void setTarget(int a) {
  if (a < ANGLE_MIN) a = ANGLE_MIN;
  if (a > ANGLE_MAX) a = ANGLE_MAX;

  // If the new command equals current *and* you still want visible motion,
  // do a tiny jog away then come back (comment out if not desired).
  if (a == currentAngle) {
    int jog = (a == ANGLE_MAX) ? (a - 4) : (a + 4);
    if (jog < ANGLE_MIN) jog = ANGLE_MIN;
    if (jog > ANGLE_MAX) jog = ANGLE_MAX;
    targetAngle = jog;
  } else {
    targetAngle = a;
  }
}

// Parse one full command line (trimmed). Returns true if handled.
bool handleCommand(const String& cmd) {
  if (cmd.length() == 0) return false;

  // Accept H/h/1 for 180, L/l/0 for 0 (works with or without newline)
  char c = cmd[0];
  if (c == 'H' || c == 'h' || c == '1') {
    setTarget(ANGLE_MAX);
    Serial.println(F("CMD: 180°"));
    return true;
  }
  if (c == 'L' || c == 'l' || c == '0') {
    setTarget(ANGLE_MIN);
    Serial.println(F("CMD: 0°"));
    return true;
  }

  // Also accept numeric "0" or "180" (or any within 0..180)
  bool allDigits = true;
  for (char ch : cmd) {
    if (ch != '-' && (ch < '0' || ch > '9')) { allDigits = false; break; }
  }
  if (allDigits) {
    int val = cmd.toInt();
    if (val >= ANGLE_MIN && val <= ANGLE_MAX) {
      setTarget(val);
      Serial.print(F("CMD: ")); Serial.print(val); Serial.println(F("°"));
      return true;
    }
  }

  Serial.println(F("Use H/1 for 180°, L/0 for 0°, or a number 0..180"));
  return false;
}

void setup() {
  s.attach(SERVO_PIN);
  s.write(currentAngle);
  Serial.begin(115200);
  Serial.println(F("Ready. Send H/1→180°, L/0→0°, or 0..180."));
}

void loop() {
  // --------- NON-BLOCKING SERIAL INPUT ---------
  static String buf;
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\r') continue;        // ignore CR
    if (c == '\n') {                 // got a line
      buf.trim();
      handleCommand(buf);
      buf = "";
    } else {
      buf += c;
      // Also handle single-char commands immediately (no newline needed)
      if (c == 'H' || c == 'h' || c == '1' || c == 'L' || c == 'l' || c == '0') {
        handleCommand(String(c));
        buf = ""; // clear partial line so CR/LF won't re-trigger
      }
    }
  }

  // --------- NON-BLOCKING MOTION UPDATE ---------
  unsigned long now = millis();
  if (now - lastStepMs >= STEP_PERIOD) {
    lastStepMs = now;

    if (currentAngle != targetAngle) {
      int dir = (targetAngle > currentAngle) ? 1 : -1;
      currentAngle += dir * STEP_DEG;

      // clamp overshoot
      if ((dir > 0 && currentAngle > targetAngle) ||
          (dir < 0 && currentAngle < targetAngle)) {
        currentAngle = targetAngle;
      }

      s.write(currentAngle);
    }
  }
}