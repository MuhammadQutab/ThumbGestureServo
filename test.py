import serial, time

PORT = "COM7"      # <-- put your exact COM here
BAUD = 115200

with serial.Serial(PORT, BAUD, timeout=0.5, write_timeout=0.5) as ser:
    time.sleep(1.5)
    print("Type H or L then Enter. Ctrl+C to quit.")
    while True:
        s = input("> ").strip().upper()
        if s in ("H","L"):
            ser.write(s.encode())
            print("sent", s)
        else:
            print("use H or L")